import subprocess
import time
import sys
import os
import signal

def run_test():
    server_process = None
    try:
        # 1. Start Server in background
        print("Starting Server in background...")
        # Use sys.executable to ensure we use the same python environment
        server_process = subprocess.Popen(
            [sys.executable, "src/servers/mcp_github_tool_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid # Create new process group
        )
        
        # Wait for server to start
        print("Waiting for server to initialize (5s)...")
        time.sleep(5)
        
        if server_process.poll() is not None:
            stdout, stderr = server_process.communicate()
            print(f"Server failed to start. Return code: {server_process.returncode}")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return

        # 2. Run Test Client
        print("Running Test Client...")
        result = subprocess.run(
            [sys.executable, "src/clients/test_client.py"],
            capture_output=True,
            text=True
        )
        
        print("\n=== Test Output ===")
        print(result.stdout)
        print("=== End Output ===")
        
        if result.returncode != 0:
            print("\n=== Test Errors ===")
            print(result.stderr)
            
    finally:
        # 3. Cleanup
        if server_process:
            print("\nStopping Server...")
            try:
                os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
                server_process.wait(timeout=5)
            except Exception as e:
                print(f"Error stopping server: {e}")
                
if __name__ == "__main__":
    run_test()
