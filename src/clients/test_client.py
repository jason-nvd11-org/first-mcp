import asyncio
import os
from dotenv import load_dotenv
from fastmcp.client import Client
from fastmcp.client.transports import SSETransport

# Load environment variables from .env file
load_dotenv()

async def main():
    """
    An example test client for the MCP GitHub Tools Server.
    """
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("ERROR: GITHUB_TOKEN not found in .env file.")
        return

    # Configure the transport to connect to the server
    # Note the /mcp/ prefix which is required by our FastAPI wrapper
    
    # --- Local Test URL ---
    # url="http://127.0.0.1:8000/mcp/sse",
    
    # --- Deployed GCP URL ---
    transport = SSETransport(
        url="https://www.jpgcp.cloud/mcp-github-tools-svc/mcp/sse",
        headers={
            "X-Github-Token": github_token
        }
    )
    
    # Create a client instance
    client = Client(transport=transport)

    # The client acts as its own async context manager for connection
    async with client as session:
        print("Connection established!")
        
        # List available tools to verify connection
        tools = await session.list_tools()
        tool_names = [t.name for t in tools]
        print(f"Available tools: {tool_names}")
        
        # --- Test Case 1: get_repo_list (without limit) ---
        print("\n--- Testing get_repo_list (without limit) ---")
        try:
            result = await session.call_tool(
                "get_repo_list", 
                {"owner": "nvd11"}
            )
            print("SUCCESS! Result:")
            print(result)
        except Exception as e:
            print(f"ERROR: {e}")

        # --- Test Case 2: get_repo_list (with limit) ---
        print("\n--- Testing get_repo_list (with limit) ---")
        try:
            result = await session.call_tool(
                "get_repo_list", 
                {"owner": "nvd11", "limit": 5}
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
                {"a": 7.0, "b": 6.0}
            )
            print("SUCCESS! Result:")
            print(result)
        except Exception as e:
            print(f"ERROR: {e}")

        # --- Test Case 4: multiply (with integers) ---
        print("\n--- Testing multiply (with integers) ---")
        try:
            result = await session.call_tool(
                "multiply", 
                {"a": 7, "b": 6}
            )
            print("SUCCESS! Result:")
            print(result)
        except Exception as e:
            print(f"ERROR: {e}")

    print("\nConnection closed.")

if __name__ == "__main__":
    asyncio.run(main())
