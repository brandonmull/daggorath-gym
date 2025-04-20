import gym.config as config
import gym.funcs as funcs
import subprocess
import time
import signal
import sys
import os
import datetime
from pathlib import Path

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Function to get current timestamp
def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

# Print more verbose information about the environment
print("==== DAGGORATH GYM TEST ====")
print(f"Working directory: {os.getcwd()}")

# Check if hash path points to system directory and warn user
hashpath = next((config.cmd[i+1] for i, arg in enumerate(config.cmd) if arg == "-hashpath" and i+1 < len(config.cmd)), None)
if hashpath:
    # Check if this is pointing to a system directory
    if "/usr/share/games/mame/hash" in hashpath:
        print("\n⚠️  WARNING: USING SYSTEM HASH DIRECTORY ⚠️")
        print("This can potentially damage your system's MAME hash files.")
        print("Please use the local hash directory by running:")
        print("  python emu/setup_hash.py")
        print("If you continue, your coco_cart.xml file may be corrupted.")
        
        response = input("\nDo you want to continue anyway? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Aborting test. Please run the setup script and try again.")
            sys.exit(1)
    else:
        # Ensure the local hash directory exists and has required files
        if not os.path.exists(hashpath):
            print(f"\n⚠️  WARNING: Local hash directory not found: {hashpath}")
            print("Running MAME may fail. Please run the setup script:")
            print("  python emu/setup_hash.py")
        elif not os.path.exists(os.path.join(hashpath, "coco_cart.xml")):
            print(f"\n⚠️  WARNING: coco_cart.xml not found in hash directory")
            print("Running MAME may fail. Please run the setup script:")
            print("  python emu/setup_hash.py")

print(f"Testing gym with command:")
for i, arg in enumerate(config.cmd):
    print(f"  [{i}] {arg}")

# Print path information
print("\nVerifying paths:")
print(f"EMU_PATH: {os.environ.get('EMU_PATH', 'Not set')}")
print(f"LUA_PATH: {os.environ.get('LUA_PATH', 'Not set')}")
print(f"LUA_CPATH: {os.environ.get('LUA_CPATH', 'Not set')}")

# Check if key files exist
print("\nVerifying files:")
autoboot_path = next((arg for i, arg in enumerate(config.cmd) if arg == "-autoboot_script" and i+1 < len(config.cmd)), None)
if autoboot_path and i+1 < len(config.cmd):
    autoboot_path = config.cmd[config.cmd.index("-autoboot_script") + 1]
    print(f"Autoboot script: {autoboot_path} (exists: {os.path.exists(autoboot_path)})")

rompath = next((config.cmd[i+1] for i, arg in enumerate(config.cmd) if arg == "-rompath" and i+1 < len(config.cmd)), None)
if rompath:
    print(f"ROM path: {rompath} (exists: {os.path.exists(rompath)})")
    # Check for daggorath.zip
    daggorath_path = os.path.join(rompath, "daggorath.zip")
    print(f"daggorath.zip: {daggorath_path} (exists: {os.path.exists(daggorath_path)})")

if hashpath:
    print(f"Hash path: {hashpath} (exists: {os.path.exists(hashpath)})")
    # Check for coco_cart.xml
    coco_cart_path = os.path.join(hashpath, "coco_cart.xml")
    print(f"coco_cart.xml: {coco_cart_path} (exists: {os.path.exists(coco_cart_path)})")
    
    # Verify daggorath ROM using MAME's verification system instead of checking XML
    print(f"Verifying daggorath ROM with MAME...")
    verify_cmd = ["mame", "-verifyroms", "daggorath", "-hashpath", hashpath]
    try:
        verify_result = subprocess.run(
            verify_cmd, 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        # Check if verification was successful
        if "romset daggorath is good" in verify_result.stdout or "daggorath" in verify_result.stdout and "is good" in verify_result.stdout:
            print(f"  - 'daggorath' ROM verified successfully")
        else:
            print(f"  - WARNING: 'daggorath' ROM verification failed")
            print(f"  - MAME output: {verify_result.stdout.strip()}")
            
            if "not found" in verify_result.stdout or "not compatible" in verify_result.stdout:
                print(f"  - ROM entry might be missing or incorrect in coco_cart.xml")
                print(f"  - Consider running: python emu/setup_hash.py")
    except Exception as e:
        print(f"  - Error verifying ROM: {e}")

# Handle Ctrl+C gracefully
def signal_handler(sig, frame):
    print(f"\n[{get_timestamp()}] Shutting down...")
    if process:
        process.terminate()
        try:
            process.wait(timeout=5)  # Wait up to 5 seconds for process to terminate
        except subprocess.TimeoutExpired:
            process.kill()  # Force kill if it doesn't terminate
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

print(f"\n[{get_timestamp()}] Opening socket...")
server_socket = funcs.open_socket()

print(f"\n[{get_timestamp()}] Starting MAME process...")
process = subprocess.Popen(
    config.cmd,
    shell=False,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1  # Line buffered
)

print(f"[{get_timestamp()}] Process started with PID: {process.pid}")

# Create log file for MAME output
log_filename = os.path.join(LOGS_DIR, f"mame_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
print(f"[{get_timestamp()}] Logging MAME output to: {log_filename}")
log_file = open(log_filename, 'w')

try:
    # Read initial output to check for immediate errors
    print(f"\n[{get_timestamp()}] Waiting for initial output...")
    stdout_initial = ""
    stderr_initial = ""
    
    # Wait up to 5 seconds for some initial output
    start_time = time.time()
    while (time.time() - start_time < 5) and process.poll() is None:
        if process.stdout.readable():
            line = process.stdout.readline()
            if line:
                timestamp = get_timestamp()
                stdout_initial += line
                log_entry = f"[{timestamp}] STDOUT: {line.strip()}"
                print(log_entry)
                log_file.write(log_entry + "\n")
                log_file.flush()
        
        if process.stderr.readable():
            line = process.stderr.readline()
            if line:
                timestamp = get_timestamp()
                stderr_initial += line
                log_entry = f"[{timestamp}] STDERR: {line.strip()}"
                print(log_entry)
                log_file.write(log_entry + "\n")
                log_file.flush()
        
        if stdout_initial or stderr_initial:
            break
        
        time.sleep(0.1)
    
    # If process already exited with error
    if process.poll() is not None and process.poll() != 0:
        print(f"\n[{get_timestamp()}] Process exited early with code: {process.poll()}")
        remaining_stdout, remaining_stderr = process.communicate()
        if remaining_stdout:
            log_entry = f"[{get_timestamp()}] STDOUT: {remaining_stdout}"
            print(log_entry)
            log_file.write(log_entry + "\n")
        if remaining_stderr:
            log_entry = f"[{get_timestamp()}] STDERR: {remaining_stderr}"
            print(log_entry)
            log_file.write(log_entry + "\n")
        sys.exit(1)
        
    # Keep the process running and monitor its output
    print(f"\n[{get_timestamp()}] Continuing to monitor process output...")
    while process.poll() is None:  # While process is still running
        # Read output (non-blocking)
        stdout_line = process.stdout.readline()
        if stdout_line:
            log_entry = f"[{get_timestamp()}] STDOUT: {stdout_line.strip()}"
            print(log_entry)
            log_file.write(log_entry + "\n")
            log_file.flush()
            
        stderr_line = process.stderr.readline()
        if stderr_line:
            log_entry = f"[{get_timestamp()}] STDERR: {stderr_line.strip()}"
            print(log_entry)
            log_file.write(log_entry + "\n")
            log_file.flush()
        
        # Add a small sleep to prevent CPU hogging
        time.sleep(0.1)
    
    # Process has exited
    return_code = process.poll()
    print(f"\n[{get_timestamp()}] Process finished with return code: {return_code}")
    
    # Explain return code
    if return_code == 0:
        print("Success: Clean exit")
    elif return_code == 1:
        print("Error: Failed to initialize")
    elif return_code == 2:
        print("Error: Invalid argument(s)")
    elif return_code == 3:
        print("Error: Missing files")
    elif return_code == 4:
        print("Error: Failed validity check")
    elif return_code == 5:
        print("Error: Fatal error")
    elif return_code == 6:
        print("Error: Game was specified but not found")
    else:
        print(f"Error: Unknown error code {return_code}")
    
    # Get any remaining output
    remaining_stdout, remaining_stderr = process.communicate()
    if remaining_stdout:
        log_entry = f"\n[{get_timestamp()}] Final STDOUT: {remaining_stdout}"
        print(log_entry)
        log_file.write(log_entry + "\n")
    if remaining_stderr:
        log_entry = f"\n[{get_timestamp()}] Final STDERR: {remaining_stderr}"
        print(log_entry)
        log_file.write(log_entry + "\n")
    
except Exception as e:
    print(f"\n[{get_timestamp()}] Error: {e}")
    if process and process.poll() is None:
        process.terminate()
finally:
    # Ensure the socket is closed
    print(f"\n[{get_timestamp()}] Closing socket...")
    server_socket.close()
    
    # Close log file
    if 'log_file' in locals():
        print(f"[{get_timestamp()}] Closing log file: {log_filename}")
        log_file.close()