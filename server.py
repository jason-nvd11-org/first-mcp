import uvicorn
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
from loguru import logger

# Import MCP server and context variable
from src.servers.mcp_github_tool_server import mcp, user_token_ctx

# ==============================================================================
# Security & Server Setup
# ==============================================================================

# Create the main FastAPI application. 
# We create a sub-application router that will be prefixed, 
# so that FastAPI's own routes (like /docs) are also correctly prefixed.
sub_app = FastAPI()

# Add middleware to handle Header (Token Passthrough)
@sub_app.middleware("http")
async def context_middleware(request: Request, call_next):
    # This middleware now operates within the sub_app, so paths are relative to the mount point.
    path = request.url.path
    if path.startswith("/mcp/sse") or path.startswith("/mcp/messages"):
        # Extract GitHub Token (Using X-Github-Token Header)
        github_token = request.headers.get("X-Github-Token")
        
        if github_token:
            # If the client provided a GitHub Token, store it in ContextVar
            user_token_ctx.set(github_token)
            logger.info(f"Received X-Github-Token from {request.client.host}")
        else:
            # If not provided, Tool will fallback to environment variables
            pass
            
    response = await call_next(request)
    return response

# Mount the FastMCP SSE app to the /mcp path within the sub-application
mcp_app = mcp.sse_app()
sub_app.mount("/mcp", mcp_app)

# Create the main application and mount the sub-application under the full prefix
app = FastAPI()
app.mount("/mcp-github-tools-svc", sub_app)

if __name__ == "__main__":
    # Run the FastAPI application using uvicorn, instead of running mcp directly
    # Port changed to 8000
    logger.info(f"Starting MCP server on port 8000. Token passthrough enabled.")
    # Bind to 0.0.0.0 to allow external access (e.g. from Docker or other machines)
    uvicorn.run(app, host="0.0.0.0", port=8000)
