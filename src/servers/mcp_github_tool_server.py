import src.configs.config  # Import to trigger config loading and logging setup
import os
import asyncio
from typing import Annotated
from loguru import logger
from pydantic import Field
from fastmcp import FastMCP
from src.services.github_service import GitHubService

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
    token: Annotated[str | None, Field(description="GitHub Personal Access Token (Optional). If not provided, server default will be used.")] = None
) -> list:
    """Fetches a list of repositories for a given GitHub user."""
    
    if token:
        # Mask the token for logging
        masked_token = f"{token[:4]}...{token[-4:]}"
        logger.info(f"Using Client-Provided Token: {masked_token}")
        service = GitHubService(_token=token)
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
    # Note: We bind to 0.0.0.0 and port 8000 for container compatibility
    logger.info("Starting FastMCP server in Streamable HTTP mode on port 8000...")
    mcp.run(transport="http", host="0.0.0.0", port=8000)
