import uvicorn
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
from loguru import logger

# Import MCP server and context variable
from src.servers.mcp_github_tool_server import mcp, user_token_ctx

# ==============================================================================
# Security & Server Setup
# ==============================================================================

# Create the main FastAPI application
app = FastAPI()

# Add middleware to handle Header (Token Passthrough)
@app.middleware("http")
async def context_middleware(request: Request, call_next):
    # Only process MCP SSE and Messages endpoints
    # Check if the path starts with the full mount path
    path = request.url.path
    if path.startswith("/mcp-github-tools-svc/mcp/sse") or path.startswith("/mcp-github-tools-svc/mcp/messages"):
        # Extract GitHub Token (Using X-Github-Token Header)
        # This is a custom header used to pass the GitHub Token through to the Tool
        github_token = request.headers.get("X-Github-Token")
        
        if github_token:
            # If the client provided a GitHub Token, store it in ContextVar
            # Note: We do not perform authentication here, we trust and pass it through
            user_token_ctx.set(github_token)
            logger.info(f"Received X-Github-Token from {request.client.host}")
        else:
            # If not provided, Tool will fallback to environment variables
            pass
            
    response = await call_next(request)
    return response

# Mount the FastMCP SSE app to the full path to ensure correct URL generation
# This path should correspond to what the application receives after the Envoy proxy.
mcp_app = mcp.sse_app()
app.mount("/mcp-github-tools-svc/mcp", mcp_app)

if __name__ == "__main__":
    # Run the FastAPI application using uvicorn, instead of running mcp directly
    # Port changed to 8000
    logger.info(f"Starting MCP server on port 8000. Token passthrough enabled.")
    # Bind to 0.0.0.0 to allow external access (e.g. from Docker or other machines)
    uvicorn.run(app, host="0.0.0.0", port=8000)
