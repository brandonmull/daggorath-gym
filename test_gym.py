import gym.config as config
import gym.funcs as funcs
import subprocess
import time
import signal
import sys

print("testing gym", config.cmd)

# Handle Ctrl+C gracefully
def signal_handler(sig, frame):
    print("\nShutting down...")
    if process:
        process.terminate()
        try:
            process.wait(timeout=5)  # Wait up to 5 seconds for process to terminate
        except subprocess.TimeoutExpired:
            process.kill()  # Force kill if it doesn't terminate
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

server_socket = funcs.open_socket()

process = subprocess.Popen(
    config.cmd,
    shell=False,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1  # Line buffered
)

print("Process started with PID:", process.pid)

try:
    # Keep the process running and monitor its output
    while process.poll() is None:  # While process is still running
        # Read output (non-blocking)
        stdout_line = process.stdout.readline()
        if stdout_line:
            print("STDOUT:", stdout_line.strip())
            
        stderr_line = process.stderr.readline()
        if stderr_line:
            print("STDERR:", stderr_line.strip())
        
        # Add a small sleep to prevent CPU hogging
        time.sleep(0.1)
    
    # Process has exited
    return_code = process.poll()
    print(f"Process finished with return code: {return_code}")
    
    # Get any remaining output
    remaining_stdout, remaining_stderr = process.communicate()
    if remaining_stdout:
        print("Final STDOUT:", remaining_stdout)
    if remaining_stderr:
        print("Final STDERR:", remaining_stderr)
    
except Exception as e:
    print(f"Error: {e}")
    process.terminate()
finally:
    # Ensure the socket is closed
    server_socket.close()