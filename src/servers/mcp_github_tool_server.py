import src.configs.config  # Import to trigger config loading and logging setup
from typing import Annotated
from loguru import logger
from contextvars import ContextVar
from pydantic import Field
from fastmcp import FastMCP
from src.services.github_service import GitHubService

# Create a ContextVar to store the user token
user_token_ctx = ContextVar("user_token", default=None)

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
    limit: Annotated[int, Field(description="The maximum number of repositories to return", default=10)] = 10
) -> list:
    """Fetches a list of repositories for a given GitHub user."""
    
    # Retrieve the token from ContextVar
    client_token = user_token_ctx.get()
    
    if client_token:
        # Mask the token for logging
        masked_token = f"{client_token[:4]}...{client_token[-4:]}"
        logger.info(f"Using Client-Provided Token: {masked_token}")
        # Use the client provided token for the service
        service = GitHubService(_token=client_token)
    else:
        logger.info("No Client Token found, using Server Environment Token.")
        # Fallback to default behavior (env var)
        service = GitHubService()

    logger.info(f"Fetching up to {limit} repositories for user: {owner}")
    repos = await service.get_repositories(owner, limit=limit)
    return repos

@mcp.resource("data://config")
def get_config() -> dict:
    """Provides the application configuration."""
    return {"theme": "dark", "version": "1.0"}
