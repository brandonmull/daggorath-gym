import os
import socket
import subprocess
import sys
import time

print("creating socket")
server_address = ("127.0.0.1", 15000) # Change the port as needed
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Create a TCP/IP socket
server_socket.bind(server_address) # Bind the socket to the address and port
server_socket.listen(1) # Listen for incoming connections

cwd = os.getcwd()

cmd = ["mame", "coco3", "daggorath",
     # Core options
     "-verbose",                                   # Show verbose output
     "-autoboot_delay", "1",                       # Delay before autoboot script runs (seconds)
     "-autoboot_script", "./src/emu/testboot.lua",   # Lua script to run at startup
     
     # ROM and path options
     "-rompath", "/usr/share/games/mame/roms",     # ROM search path
     "-hashpath", "/usr/share/games/mame/hash",     # ROM search path
     "-pluginspath", "/usr/share/games/mame/plugins", # Plugins path
     
     # Video options
     "-window",                                    # Run in a window (not fullscreen)
     "-resolution", "1280x960",                    # Window resolution
    #  "-waitvsync",                                 # Wait for vertical sync
    #  "-refresh", "60",                             # Refresh rate
    #  "-prescale", "1",                             # Scale before any effects
     
     # Audio options
    #  "-sound", "sdl",                              # Use SDL sound output
    #  "-samplerate", "48000",                       # Audio sample rate
    #  "-volume", "-5",                              # Initial volume (-32 to 0)
    ]

print(cmd)

process = subprocess.Popen(
    cmd,
    shell=False,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Run the subprocess
while True:
    if process.stderr is not None:
        error = process.stderr.readline()
        if (error != ""):
            print(error)
            process.stderr.flush()
        
    if process.stdout is not None:
        output = process.stdout.readline()
        if (output != ""):
            print(output)
            process.stdout.flush()
        if output == "did it":
            print("yaaaay!")
            exit(0)

try:
    print("waiting on socket")
    client_socket, client_address = server_socket.accept() # Wait for a connection
    print(f"socket connected: {client_address}")
    while True:
        data = client_socket.recv(1024) # Receive data from the client
        if data:
            print(data.decode())
except Exception as e:
    print(f"error: {e}")
finally:
    print("cleaning up")
    client_socket = None  # Initialize in case the exception occurs before client_socket is assigned
    if 'client_socket' in locals() and client_socket:
        client_socket.close() # Close the client socket
    server_socket.close() # Close the server socket
    process.kill() # Terminate the subprocess

