import src.configs.config  # Import to trigger config loading and logging setup
import os
import asyncio
from typing import Annotated
from loguru import logger
from contextvars import ContextVar
from pydantic import Field
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastmcp import FastMCP
from src.services.github_service import GitHubService

# Create a ContextVar to store the user token
user_token_ctx = ContextVar("user_token", default=None)

# Define Middleware to capture Token from Header
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Extract X-Github-Token header
        token = request.headers.get("X-Github-Token")
        if token:
            user_token_ctx.set(token)
            logger.info(f"Captured X-Github-Token from {request.client.host}")
        return await call_next(request)

# Create a basic server instance with instructions
mcp = FastMCP(
    name="MyAssistantServer",
    instructions="""
    This server provides specialized GitHub tools. 
    IMPORTANT: When asked for GitHub repositories, you MUST use the `get_repo_list` tool. 
    DO NOT use terminal commands like `gh` or open the browser for this task.
    """
)

@mcp.tool()
def multiply(
    a: Annotated[float, Field(description="The first number to multiply")], 
    b: Annotated[float, Field(description="The second number to multiply")]
) -> float:
    """Multiplies two numbers together."""
    logger.info(f"Multiplying {a} and {b}")
    return a * b

@mcp.tool()
async def get_repo_list(
    owner: Annotated[str, Field(description="The GitHub username or organization name")], 
    limit: Annotated[int, Field(description="The maximum number of repositories to return", default=10)] = 10,
    token: Annotated[str | None, Field(description="GitHub Personal Access Token (Optional). If not provided, checks Header or server default.")] = None
) -> list:
    """Fetches a list of repositories for a given GitHub user."""
    
    # 1. Try explicit argument
    # 2. Try ContextVar (Header)
    # 3. Fallback to None (Service will use Env)
    final_token = token or user_token_ctx.get()
    
    if final_token:
        # Mask the token for logging
        masked_token = f"{final_token[:4]}...{final_token[-4:]}"
        logger.info(f"Using Client-Provided Token: {masked_token}")
        service = GitHubService(_token=final_token)
    else:
        logger.info("No Client Token provided, using Server Environment Token.")
        service = GitHubService()

    logger.info(f"Fetching up to {limit} repositories for user: {owner}")
    repos = await service.get_repositories(owner, limit=limit)
    return repos

@mcp.resource("data://config")
def get_config() -> dict:
    """Provides the application configuration."""
    return {"theme": "dark", "version": "1.0"}

if __name__ == "__main__":
    # Start the server using Streamable HTTP transport
    # Inject our AuthMiddleware to handle headers
    # Cloud Run injects the PORT environment variable
    port = int(os.getenv("PORT", 8000))
    # We set the path to match the full Envoy path so that relative URLs work correctly
    # Envoy passes the full path /mcp-github-tools-svc/mcp without rewriting
    mcp_path = "/mcp-github-tools-svc/mcp"
    logger.info(f"Starting FastMCP server in Streamable HTTP mode on port {port} at path {mcp_path}...")
    mcp.run(
        transport="http", 
        host="0.0.0.0", 
        port=port, 
        middleware=[Middleware(AuthMiddleware)],
        path=mcp_path
    )
