import asyncio
import os
from dotenv import load_dotenv
from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport

# Load environment variables from .env file
load_dotenv()

async def main():
    """
    An example test client for the MCP GitHub Tools Server using Streamable HTTP.
    """
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("ERROR: GITHUB_TOKEN not found in .env file.")
        return

    # Configure the transport to connect to the server
    
    # --- Local Test URL ---
    # Note: Server is now mounted at /mcp-github-tools-svc/mcp for Envoy compatibility
    # url = "http://127.0.0.1:8000/mcp-github-tools-svc/mcp"
    
    # --- Deployed GCP URL (Direct) ---
    # url = "https://mcp-github-tools-svc-7hq3m4pdya-nw.a.run.app/mcp"

    # --- Deployed GCP URL (Via Envoy) ---
    url = "https://www.jpgcp.cloud/mcp-github-tools-svc/mcp"

    # Pass the GitHub Token via HTTP Headers
    # This tests the AuthMiddleware and ContextVar logic
    transport = StreamableHttpTransport(
        url=url,
        headers={
            "X-Github-Token": github_token
        }
    )
    
    # Create a client instance
    client = Client(transport=transport)

    # Use an async context manager to handle the session
    try:
        async with client as session:
            print("Connection established!")
            
            # List available tools to verify connection
            tools = await session.list_tools()
            tool_names = [t.name for t in tools]
            print(f"Available tools: {tool_names}")
            
            # --- Test Case 1: get_repo_list (without limit, token via Header) ---
            print("\n--- Testing get_repo_list (token via Header) ---")
            try:
                # Note: We do NOT pass 'token' in arguments here.
                # The server should pick it up from the X-Github-Token header we configured in transport.
                result = await session.call_tool(
                    "get_repo_list", 
                    arguments={
                        "owner": "nvd11"
                    }
                )
                print("SUCCESS! Result:")
                print(result)
            except Exception as e:
                print(f"ERROR: {e}")

            # --- Test Case 2: get_repo_list (with limit, explicit token override) ---
            print("\n--- Testing get_repo_list (explicit token override) ---")
            try:
                # Even with Header present, explicit argument should take precedence (or work just as well)
                result = await session.call_tool(
                    "get_repo_list", 
                    arguments={
                        "owner": "nvd11", 
                        "limit": 5,
                        "token": github_token
                    }
                )
                print("SUCCESS! Result:")
                print(result)
            except Exception as e:
                print(f"ERROR: {e}")

            # --- Test Case 3: multiply (with floats) ---
            print("\n--- Testing multiply (with floats) ---")
            try:
                result = await session.call_tool(
                    "multiply", 
                    arguments={"a": 7.0, "b": 6.0}
                )
                print("SUCCESS! Result:")
                print(result)
            except Exception as e:
                print(f"ERROR: {e}")

        print("\nConnection closed.")

    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
