MAME Lua and Python Socket Communication HistoryUser: I am running an old game inside the mame emulator and capturing game state with a custom Lua script, which executes inside mame. I need to import a well known Lua package for socket communication but I dont think the import is actually working due to the way mame is configured to run Lua. It might be the way Im installing Lua packages to my system, such that they can be found by the Lua executable running inside mame.AI: MAME uses an embedded Lua environment that does not read your system’s global Lua environment variables (LUA_PATH or LUA_CPATH). It only looks inside its own root or relative directory structure for files.Furthermore, luasocket relies on a compiled C library (socket/core.so or socket/core.dll). MAME's embedded Lua interpreter will throw architecture mismatch errors if your system's Lua version doesn't perfectly match MAME's internal Lua version.To fix this, you must explicitly inject the file paths inside your script or use MAME's built-in TCP features.Option 1: Inject the Paths at the Top of Your ScriptIf you want to use your existing luasocket installation, you must manually point MAME's engine to your system's luarocks or Lua install directories before calling require.Add this block to the very top of your custom Lua script:lua-- Standard system paths for LuaSocket (Adjust version numbers to match your system)
package.path = package.path .. ";/usr/local/share/lua/5.3/?.lua;/usr/local/share/lua/5.3/?/init.lua"
package.cpath = package.cpath .. ";/usr/local/lib/lua/5.3/?.so"

-- For Windows Users (Example using LuaRocks default paths):
-- package.path = package.path .. ";C:\\luarocks\\share\\lua\\5.3\\?.lua"
-- package.cpath = package.cpath .. ";C:\\luarocks\\lib\\lua\\5.3\\?.dll"

local socket = require("socket")
Use code with caution.Option 2: The Portable / Local Setup (Recommended)To keep your script completely independent of system settings, place the library files directly into your MAME directory.Create a modules folder inside your main MAME directory.Move the socket.lua file and the socket folder (containing core.so or core.dll) into it.Format the top of your script like this:lua-- Force MAME to look into your local module folder
package.path = package.path .. ";./modules/?.lua;./modules/?/init.lua"
package.cpath = package.cpath .. ";./modules/?.so;./modules/?.dll"

local socket = require("socket")
Use code with caution.Option 3: Use MAME’s Built-in Sockets (No Imports Needed)MAME actually provides a native, built-in network socket wrapper through its emu.file API. This is completely secure, requires zero external installations, and never suffers from version mismatch crashes.To open a connection and send data:lua-- "rwc" stands for Read/Write/Create
local client = emu.file("rwc") 

-- Connects to localhost on port 12345
local error_code = client:open("socket.127.0.0.1:12345") 

if not error_code then
    -- Extract your game state data
    local game_score = manager:machine():outputs():get_value("score")
    
    -- Send it out over the socket
    client:write(tstring(game_score) .. "\n")
end
Use code with caution.If you prefer to continue debugging your luasocket implementation, let me know:What Operating System you are running (Windows, Mac, or Linux)?The exact error message MAME outputs when it tries to run your script.User: emu.file is for sockets not files?AI: emu.file handles both files and network sockets.Under the hood, MAME's core C++ engine handles file and network I/O through a unified interface. Since POSIX/Unix systems traditionally treat network sockets as files, MAME's developers exposed network features directly through the emu.file wrapper in Lua.If you pass a typical file path to emu.file:open(), it reads or writes a file on your hard drive. However, if you prefix the string argument with "socket.", the interpreter intercepts the instruction, skips the local disk, and establishes a TCP network connection instead:lualocal comm_pipe = emu.file("rwc")

-- Passing "socket.IP:PORT" changes the mode from File I/O to Network I/O
comm_pipe:open("socket.127.0.0.1:12345") 
Use code with caution.How the MAME Socket BehavesIt functions bi-directionally: If a listening server is already running on that port, emu.file connects as a client. If no server exists, it binds to the port and behaves as a listening server waiting for an incoming connection.No luasocket overhead: You avoid architecture version mismatch issues, compiled C dependency injections, or manual path-hacking.Would you like help adapting your script's logic to send or stream your extracted game state over this native abstraction?User: socket communication is intended to occur with a parent python script that starts the mame emulator and game. the lua script needs to publish game state to the socket for the parent process to consume.AI: Using MAME’s native emu.file API is the most stable approach for this architecture.Because the Python script launches MAME as a subprocess, the Python script must act as the TCP Server and start listening before spawning the MAME process. When MAME boots, the embedded Lua script will automatically connect as a client and stream the game state.1. The Parent Python Script (parent.py)This script initializes a basic non-blocking or blocking TCP server on port 12345 and launches MAME using the -autoboot_script argument to inject your Lua watcher.pythonimport socket
import subprocess
import time

HOST = "127.0.0.1"
PORT = 12345

# 1. Create and bind the TCP server socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(1)
print(f"[Python] Server listening on {HOST}:{PORT}...")

# 2. Launch MAME as a subprocess, pointing to your game and Lua script
# Adjust the executable path and game name (e.g., 'pacman') as needed
mame_cmd = [
    "mame", 
    "pacman", 
    "-autoboot_script", "game_watcher.lua",
    "-skip_gameinfo"
]
print("[Python] Launching MAME subprocess...")
mame_process = subprocess.Popen(mame_cmd)

# 3. Accept the incoming connection from MAME's Lua script
conn, addr = server_socket.accept()
print(f"[Python] MAME connected from {addr}")

# 4. Consume the game state stream
try:
    buffer = ""
    while mame_process.poll() is None:  # While MAME is running
        data = conn.recv(1024).decode('utf-8')
        if not data:
            break
        
        buffer += data
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            if line.strip():
                print(f"[Game State Received]: {line}")
                
except KeyboardInterrupt:
    print("[Python] Terminating...")
finally:
    conn.close()
    server_socket.close()
    mame_process.terminate()
Use code with caution.2. The Internal MAME Lua Script (game_watcher.lua)This script initializes the connection via emu.file and uses MAME's frame callback registration to stream memory values to Python every single frame.lualocal socket = emu.file("rwc")
local is_connected = false

-- Attempt to connect to the Python parent script
local error_code = socket:open("socket.127.0.0.1:12345")

if not error_code then
    print("[Lua] Successfully connected to Python parent server!")
    is_connected = true
else
    print("[Lua] Connection failed. Is the Python script listening?")
end

-- Core MAME Frame Hook
emu.register_frame(function()
    if not is_connected then return end

    -- Example: Extracting state from RAM 
    -- Replace with your actual game variables / CPU memory regions
    local main_cpu = manager:machine():devices(":maincpu")
    if main_cpu then
        local mem = main_cpu:spaces("program")
        
        -- Pull dummy metrics (replace 0x1234 with your target memory offsets)
        local score = mem:read_u32(0x1234)
        local lives = mem:read_u8(0x5678)
        
        -- Package payload as a clean, single-line string format (like JSON or CSV)
        local payload = string.format('{"score": %d, "lives": %d}\n', score, lives)
        
        -- Publish straight to Python
        socket:write(payload)
    end
end)
Use code with caution.Key Technical DetailsTiming Sequence: Python must listen before MAME boots. If MAME boots first, emu.file will try to bind as a server instead of a client, causing a conflict when Python tries to open the same port.The Newline \n Anchor: In socket streaming, packets can fragment. Appending \n in Lua and splitting on \n in Python ensures your data strings are safely parsed frame by frame without corruption.What specific data profiles are you scraping from memory (raw bytes, player coordinates, scores)? I can write the precise memory-read loop parsing logic for your target game.User: what happens if python accepts before lua sends signal? what happens if python accepts after lua sends signal?AI: To understand how Python and MAME interact, it helps to know that TCP sockets are managed by your Operating System's network stack, not by the scripts themselves. The OS maintains a "backlog queue" that holds connections until the scripts are ready for them.The behavior changes based on the order of execution.Scenario A: Python calls .accept() BEFORE Lua sends a signalThis is the standard, intended behavior for the Python-server/Lua-client architecture.Python Blocks: Python reaches server_socket.accept() and pauses execution. It sits there patiently, consuming zero CPU, waiting for a connection request.MAME Bootstraps: MAME loads up and fires your Lua script.The Connection (The "Signal"): Lua executes socket:open("socket.127.0.0.1:12345"). This transmits a TCP SYN packet to the OS network stack.Instant Match: The OS instantly pairs MAME's connection request with Python’s waiting .accept() call.Data Flow Begins: Python instantly unblocks, moves past .accept(), and enters the while loop to process the game data. No data is lost.Scenario B: Python calls .accept() AFTER Lua sends a signalThis happens if MAME loads incredibly fast and runs its Lua script before the Python script finishes its setup and reaches the .accept() line.Lua Knocks on the Door: Lua runs socket:open(...) and sends its initial TCP connection request.The OS Backlog Queue Saves It: Because Python already called server_socket.bind() and server_socket.listen(1), your operating system says: "Python isn't actively looking at me right now, but it told me to expect visitors."Connection Handshake Completes: The OS automatically completes the TCP connection handshake with MAME's Lua script. MAME’s socket:open() evaluates to successful (no error code).Data Buffering: Because Lua thinks the connection is fully active, it will immediately start writing data payloads using socket:write(). The OS takes this game state data and holds it safely inside a kernel network buffer.Python Catches Up: A few milliseconds later, Python finally reaches server_socket.accept().Flush to Python: Python instantly returns from the .accept() call, looks at the socket buffer, and processes all the backlogged game frames that Lua sent during the delay. No data is lost.⚠️ The Real Trap: Python hasn't called .listen() yetThe only way this communication breaks entirely is if MAME sends its signal before Python even sets up the server port (before .bind() or .listen()).If Lua calls socket:open() and the OS sees that port 12345 is completely closed:MAME's socket:open() will immediately fail and return an error code.Depending on how you handle that error, your Lua script will either crash, completely skip the connection hook, or MAME will default into a listening server role. Python will later crash with an Address already in use error when it tries to start.How to ensure a perfect connection sequenceIf you want to guarantee they synchronize seamlessly every time without racing each other, add a tiny boot delay to your Python script's subprocess call to let the server socket fully mature:pythonserver_socket.bind((HOST, PORT))
server_socket.listen(1)

# Give the OS network stack a split second to claim the port before MAME boots
time.sleep(0.5) 

mame_process = subprocess.Popen(mame_cmd)
conn, addr = server_socket.accept()
Use code with caution.If you are noticing game state drops or script crashes when launching, let me know if you are seeing connection errors on the Python console or if MAME freezes on startup.User: in the sample pytgon script you gave, why not call accept before running mame?AI: Calling accept() before launching MAME will cause your script to freeze completely. Your Python script will hang forever, and MAME will never launch.Here is why:The accept() BlockThe server_socket.accept() method is blocking by default. When Python runs that line, it stops execution entirely. It sits and waits for a network client to connect. It will not execute the next line of code until a connection arrives.The DeadlockIf you switch the order, you create a classic deadlock situation:Python calls accept() and pauses execution, waiting for a client.Python is frozen, so it never reaches the subprocess.Popen(mame_cmd) line.MAME never launches, meaning your Lua script never runs.The Lua script never connects, so Python stays frozen forever.The Correct Order of OperationsTo break this deadlock, you must launch MAME first using subprocess.Popen:server_socket.listen(1): Tells the operating system to open the port and queue up any incoming connections.subprocess.Popen(...): Launches MAME in the background. Unlike other execution methods, Popen is non-blocking. It kicks off MAME and instantly returns control to Python.server_socket.accept(): Python now safely blocks and waits. Meanwhile, MAME is booting up in the background and will connect a second later, unblocking Python.Are you running into an error where MAME boots too fast and fails to connect before Python is ready? If so, we can add a slight delay or handle reconnection loops in Lua.User: I seeAI: It is a very easy trap to fall into when writing network scripts!Using subprocess.Popen followed immediately by accept() creates the perfect hand-off: MAME is given the green light to start initializing, and Python is immediately in position waiting to catch its connection.If you want to make your Lua code incredibly robust against any future startup timing issues, you can wrap the connection logic in a simple retry loop inside MAME's initialization phase.Here is how you can write the Lua side so it keeps trying to connect until Python is fully ready:lualocal socket = emu.file("rwc")
local is_connected = false

-- Keep looping until the connection succeeds
while not is_connected do
    print("[Lua] Attempting to connect to Python parent...")
    local error_code = socket:open("socket.127.0.0.1:12345")
    
    if not error_code then
        print("[Lua] Connected successfully!")
        is_connected = true
    else
        print("[Lua] Python not ready yet. Retrying in 1 second...")
        -- Standard MAME way to pause execution briefly without crashing
        emu.wait(1.0) 
    end
end
Use code with caution.Would you like to look at how to structure your game data (like player positions or health) into a clean format like JSON so Python can easily read and parse it on the other side?User: for now, let's assume we use mames built-in tcpAI: Using MAME's built-in TCP stack through emu.file is the absolute cleanest choice. It removes all installation dependencies and eliminates version mismatches.Since you are locking in this architecture, here is a complete, production-ready blueprint of the exact execution behavior, data format, and life-cycle management for your system.1. Data Schema Architecture (JSON Stream)Because TCP treats data as a continuous stream of bytes rather than distinct packets, frames can merge or split mid-transmission.The industry standard for solving this in game-state extraction is a Newline-Delimited JSON (NDJSON) Stream.Every game frame, Lua outputs exactly one self-contained JSON object.Every object ends with a strict \n newline character.Python reads line-by-line, perfectly slicing the data back into frames.2. The Complete MAME Lua Script (game_watcher.lua)Save this script inside your main MAME directory. It safely handles the OS networking handshake, reads raw emulator memory, and streams the updates.lualocal socket = emu.file("rwc")
local is_connected = false

-- Step 1: Establish the OS Network Handshake
local error_code = socket:open("socket.127.0.0.1:12345")

if not error_code then
    print("[MAME Lua] Successfully bound/connected via native TCP.")
    is_connected = true
else
    print("[MAME Lua] Failed to open network socket: " .. tostring(error_code))
end

-- Step 2: Register the Frame Callback Loop
emu.register_frame(function()
    if not is_connected then return end

    -- Locate the primary emulation CPU (Adjust ":maincpu" if your driver differs)
    local main_cpu = manager:machine():devices(":maincpu")
    if main_cpu then
        local mem = main_cpu:spaces("program")
        
        -- Pull live variables from the emulator's memory space
        -- Replace these hex offsets with your specific game's memory map
        local p1_score  = mem:read_u32(0x00FF00) 
        local p1_lives  = mem:read_u8(0x00FF04)
        local p1_x_pos  = mem:read_u16(0x00FF08)
        local game_over = mem:read_u8(0x00FF0A)

        -- Serialize to a strict single-line JSON string ending in \n
        local payload = string.format(
            '{"score": %d, "lives": %d, "x_pos": %d, "game_over": %d}\n',
            p1_score, p1_lives, p1_x_pos, game_over
        )
        
        -- Fire over the native TCP interface
        socket:write(payload)
    end
end)
Use code with caution.3. The Orchestration Python Script (parent.py)This script provisions the server socket, fires up MAME in a decoupled process, catches the incoming connection, and decodes the real-time JSON stream.pythonimport socket
import subprocess
import json
import sys

HOST = "127.0.0.1"
PORT = 12345

# Step 1: Initialize and bind the OS socket server
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(1)
print(f"[Python] TCP Server armed on {HOST}:{PORT}")

# Step 2: Spawn MAME completely decoupled (Non-blocking)
# Adjust "pacman" to your target game ROM shortname
mame_command = [
    "mame", "pacman", 
    "-autoboot_script", "game_watcher.lua",
    "-skip_gameinfo",
    "-window"
]
print("[Python] Launching MAME engine...")
mame_process = subprocess.Popen(mame_command)

# Step 3: Block execution here to catch MAME's immediate startup connection
print("[Python] Waiting for MAME Lua handshake...")
connection, client_address = server_socket.accept()
print(f"[Python] Telemetry link established with MAME at {client_address}")

# Step 4: Stream and consume game state frame-by-frame
try:
    network_buffer = ""
    
    # Process data while the MAME window remains open
    while mame_process.poll() is None:
        raw_chunk = connection.recv(4096).decode('utf-8')
        if not raw_chunk:
            break # Socket closed gracefully by remote end
            
        network_buffer += raw_chunk
        
        # Extract individual frames using our newline anchor
        while "\n" in network_buffer:
            line, network_buffer = network_buffer.split("\n", 1)
            line = line.strip()
            
            if line:
                try:
                    # Safely deserialize the frame into a native Python dictionary
                    frame_state = json.loads(line)
                    
                    # Target your logic here (e.g., Feed to an AI agent, print, log)
                    print(f"Frame Telemetry -> Score: {frame_state['score']} | X-Pos: {frame_state['x_pos']}")
                    
                    if frame_state['game_over'] == 1:
                        print("[Python] Game over state detected via telemetry.")
                        
                except json.JSONDecodeError:
                    print(f"[Warning] Fragmented or corrupt frame ignored: {line}")

except KeyboardInterrupt:
    print("\n[Python] Halting tracking via user interruption.")
finally:
    # Step 5: Clean up all resources and close the background process cleanly
    print("[Python] Cleaning up socket descriptors and processes...")
    connection.close()
    server_socket.close()
    if mame_process.poll() is None:
        mame_process.terminate()
        mame_process.wait()
    print("[Python] Closed cleanly.")
Use code with caution.If you are ready to start pointing this at your target game, let me know:What game are you running?Do you already have the exact memory hex addresses for the values you want to track?User: I thought lua socket would get success even if python hasn't accepted yet.AI: You are completely correct to think that, and your mental model of networking is spot on! The Lua socket will return a success status before Python calls accept().The confusion comes down to a slight difference between how a network handshake works at the hardware/OS level versus how the application code reacts to it.Here is exactly what happens behind the scenes:1. The OS Completes the Connection EarlyWhen Python runs these two lines:pythonserver_socket.bind(("127.0.0.1", 12345))
server_socket.listen(1)
Use code with caution.Python tells the operating system: "I am officially reserving Port 12345. If anyone knocks on the door, let them in and put them in the waiting room (the backlog queue)."When MAME launches right after and Lua executes socket:open("socket.127.0.0.1:12345"), the operating system immediately completes the full TCP connection handshake with Lua. Because the OS says "Yes, this port is open and listening," Lua’s socket:open() successfully finishes and returns no error.As far as Lua is concerned, it is 100% connected, even though Python is still completely oblivious to it.2. Why Python Still Freezes If Put FirstIf you were to change the code order to call accept() before spawning MAME, the network connection itself would still technically work just fine, but Python creates a logical deadlock on its own thread.Here is the step-by-step breakdown of why it locks up:python# 1. This works fine. Port is opened by the OS.
server_socket.listen(1)

# 2. Python freezes right here. 
# It tells the OS: "Do not move to the next line of code until you pull someone out of the waiting room and give them to me."
connection, addr = server_socket.accept() 

# 3. Python can never reach this line!
mame_process = subprocess.Popen(mame_command) 
Use code with caution.Because Python stops execution entirely at line 2, line 3 is never read. MAME is never turned on, the Lua script never boots, nobody ever knocks on the door, and Python waits in that exact spot forever.SummaryDoes Lua get a success status before Python accepts? Yes. The operating system handles it immediately.Why can't we accept first? Because Python refuses to run the next line of code (launching MAME) until after it pulls a connection out of the queue.By running subprocess.Popen first, you kick off MAME, Python immediately moves to the next line, calls accept(), and instantly grabs the connection the OS just queued up.Do you want to see how to make Python handle multiple games or automatic restarts if MAME closes?User: I meant that, in your lua script for detecting connection, you rely on error code which would return success even if python hasn't acceptedAI: Ah, I see exactly what you mean now! You are entirely correct, and that was a sharp catch.Because socket:open() returns success the moment the Operating System places the connection into the backlog queue, checking the error_code only proves that the port is open—it cannot guarantee that the Python script has actively called accept() and is ready to read the stream.If Python is delayed in calling accept() (for example, if it is busy importing heavy libraries or initializing an AI framework), Lua will happily assume it is fully connected and start dumping data into the OS buffer immediately. If that buffer fills up before Python wakes up, Lua could choke or drop frames.To truly confirm that Python has accepted the connection and is actively listening, you need a two-way application handshake.Here is how to modify both scripts so Lua waits for a literal "green light" signal from Python before it starts firing game frames.1. The Updated Lua Script (game_watcher.lua)Instead of just relying on the error_code, Lua will connect, pause, and wait until it reads a specific confirmation string (like "READY") sent by Python after Python clears the accept() line.lualocal socket = emu.file("rwc")
local is_connected = false

-- 1. This succeeds as soon as the OS accepts the connection into the queue
local error_code = socket:open("socket.127.0.0.1:12345")

if not error_code then
    print("[MAME Lua] Port open. Waiting for Python application handshake...")
    
    -- 2. Block/Loop here until Python explicitly sends the "READY" confirmation
    local handshaken = false
    while not handshaken do
        -- Read up to 10 bytes from the socket
        local response = socket:read(10)
        
        if response and string.find(response, "READY") then
            print("[MAME Lua] Handshake confirmed! Python is actively listening.")
            handshaken = true
            is_connected = true
        else
            -- Pause for a brief moment before checking the socket again
            emu.wait(0.1) 
        end
    end
else
    print("[MAME Lua] Failed to open network socket: " .. tostring(error_code))
end

-- 3. Core Frame Loop (Only runs after is_connected becomes true)
emu.register_frame(function()
    if not is_connected then return end

    -- (Your game state reading and socket:write logic goes here)
end)
Use code with caution.2. The Updated Python Script (parent.py)Once Python passes the blocking accept() call, it immediately writes "READY\n" back through the socket to give MAME the authorization to begin tracking.python# ... (Previous socket setup and subprocess.Popen code remains the same) ...

print("[Python] Waiting for MAME Lua connection...")
connection, client_address = server_socket.accept()
print(f"[Python] Connection pulled from queue. Sending application handshake...")

# Send the explicit green light signal to Lua
connection.sendall(b"READY\n")
print("[Python] Handshake sent. Streaming initialized.")

# ... (Proceed to your connection.recv loop to process the frames) ...
Use code with caution.By adding this simple read-verify step, you ensure your Python backend is 100% synchronized and initialized before a single frame of game telemetry is ever spent.Does this match the level of execution safety you were looking to build into your pipeline?User: im fine with trying the simple way and relying on os to queue up signals from lua until python acceptsAI: That makes perfect sense. For standard game extraction pipelines, relying entirely on the operating system's built-in TCP queue is highly reliable and keeps your codebase beautifully simple.The OS backlog queue can easily hold thousands of bytes without dropping anything, meaning MAME can start booting, loading its drivers, and writing early frame data while Python is still waking up. Everything will just queue up smoothly and flush into Python the exact millisecond accept() finishes.To get your script up and running right now without any unnecessary overhead, here is the streamlined, plug-and-play setup.The Streamlined Lua Script (game_watcher.lua)lualocal socket = emu.file("rwc")
socket:open("socket.127.0.0.1:12345") -- OS immediately queues this up

emu.register_frame(function()
    local main_cpu = manager:machine():devices(":maincpu")
    if main_cpu then
        local mem = main_cpu:spaces("program")
        
        -- Pull your game metrics (Change these offsets/sizes to your specific game)
        local score = mem:read_u32(0x00FF00)
        local lives = mem:read_u8(0x00FF04)
        
        -- Format as a single line ending with \n so the OS can stream it safely
        local payload = string.format('{"score": %d, "lives": %d}\n', score, lives)
        socket:write(payload)
    end
end)
Use code with caution.The Streamlined Python Script (parent.py)pythonimport socket
import subprocess
import json

# 1. Bind port and tell the OS to maintain a connection queue
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(("127.0.0.1", 12345))
server_socket.listen(1)

# 2. Fire and forget MAME launch (Replace 'pacman' with your target game ROM)
mame_process = subprocess.Popen(["mame", "pacman", "-autoboot_script", "game_watcher.lua", "-skip_gameinfo"])

# 3. Pull MAME from the OS queue (blocks briefly until MAME hits the socket line)
conn, addr = server_socket.accept()

# 4. Stream the data straight out of the OS network buffer
try:
    buffer = ""
    while mame_process.poll() is None:
        data = conn.recv(4096).decode('utf-8')
        if not data: 
            break
        
        buffer += data
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            if line.strip():
                state = json.loads(line)
                print(f"[Game State] Score: {state['score']} | Lives: {state['lives']}")
finally:
    conn.close()
    server_socket.close()
    if mame_process.poll() is None:
        mame_process.terminate()
Use code with caution.If you are ready to start pointing this at your target game, let me know:What arcade game are you looking to track?Do you need any help mapping out its RAM memory addresses to extract things like player coordinates, health, or stage numbers?User: I just want a working poc before I complicate the communication protocol between thesevprocessesAI: This is the absolute best way to build a pipeline: get a minimal, verified proof-of-concept (PoC) working before dealing with JSON, data schemas, or complex memory maps.This bare-minimum PoC strips out all external parsing logic. The Lua script simply counts frames and throws a raw number string over the socket. Python grabs it and prints it directly to your terminal.1. Save as game_watcher.luaPlace this file in your main MAME directory. It doesn't read any game memory yet; it just counts emulator frames and streams the plain text.lualocal socket = emu.file("rwc")
socket:open("socket.127.0.0.1:12345")

local frame_count = 0

emu.register_frame(function()
    frame_count = frame_count + 1
    
    -- Send a simple, plain text line: "Frame: X"
    socket:write("Frame: " .. tostring(frame_count) .. "\n")
end)
Use code with caution.2. Save as parent.pyPlace this script in your main MAME directory as well. Run this script using python parent.py.pythonimport socket
import subprocess

# 1. Arm the OS socket receiver
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(("127.0.0.1", 12345))
server_socket.listen(1)
print("[Python] Server listening...")

# 2. Launch MAME in the background 
# (Using 'pacman' as a dummy placeholder—swap to any working ROM name you have)
mame_cmd = ["mame", "pacman", "-autoboot_script", "game_watcher.lua", "-skip_gameinfo", "-window"]
print("[Python] Starting MAME subprocess...")
mame_process = subprocess.Popen(mame_cmd)

# 3. Pull the connection from the OS queue
conn, addr = server_socket.accept()
print(f"[Python] Connected to MAME at {addr}!")

# 4. Stream and print the raw text strings directly
try:
    buffer = ""
    while mame_process.poll() is None:
        data = conn.recv(1024).decode('utf-8')
        if not data:
            break
        
        buffer += data
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            if line.strip():
                print(f"[Received] {line}")
                
except KeyboardInterrupt:
    pass
finally:
    print("[Python] Shutting down clean...")
    conn.close()
    server_socket.close()
    if mame_process.poll() is None:
        mame_process.terminate()
Use code with caution.To Verify It Works:Run python parent.py in your terminal.MAME will pop up, load the game, and start running.Your Python terminal will instantly start scrolling with a live counter: [Received] Frame: 1, [Received] Frame: 2, [Received] Frame: 3, etc.Once you verify this stream is scrolling in your terminal, let me know if it runs successfully or if you hit any file/path errors when Python tries to execute MAME.User: I dont care what thevmessage is at first. I just want to start with verifying lua can talk to pythonAI: Here is the absolute simplest verification proof of concept.The Lua script sends one single word immediately upon booting up. Python catches it, prints it, and instantly closes everything down. This proves the connection works without even needing the game to run frames.1. Save as game_watcher.lualualocal socket = emu.file("rwc")
socket:open("socket.127.0.0.1:12345")

-- Send a single verification signal and stop
socket:write("PING\n")
Use code with caution.2. Save as parent.pypythonimport socket
import subprocess

# 1. Listen for MAME
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(("127.0.0.1", 12345))
server_socket.listen(1)

# 2. Launch MAME (using 'pacman' or any valid ROM name you own)
mame_process = subprocess.Popen(["mame", "pacman", "-autoboot_script", "game_watcher.lua", "-skip_gameinfo", "-window"])

# 3. Accept connection and read the single message
conn, addr = server_socket.accept()
message = conn.recv(1024).decode('utf-8').strip()

# 4. Print the result and kill the process immediately
print(f"\n[SUCCESS] Connection Verified! Lua sent: '{message}'\n")

conn.close()
server_socket.close()
mame_process.terminate()
Use code with caution.Run python parent.py. If you see [SUCCESS] Connection Verified! Lua sent: 'PING' on your screen, your inter-process communication link is officially working.Let me know if the message pops up successfully or if MAME throws an error finding the script.User: how would I write a kill switch if message is never received?AI: To prevent Python from freezing forever if MAME fails or the Lua script crashes on startup, you can add a socket timeout.By calling server_socket.settimeout(seconds), you tell the operating system to automatically break the blocking accept() call if MAME does not connect within your specified time limit. Python can then catch this error, cleanly kill the orphaned MAME process, and exit.Here is the updated, bulletproof verification script:Save as parent.pypythonimport socket
import subprocess

# 1. Initialize the socket server
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(("127.0.0.1", 12345))
server_socket.listen(1)

# 2. Set the Kill Switch Timeout (e.g., 5 seconds)
# If no connection happens within 5 seconds, Python will wake up and throw an exception
server_socket.settimeout(5.0)

# 3. Launch MAME in the background
mame_process = subprocess.Popen(["mame", "pacman", "-autoboot_script", "game_watcher.lua", "-skip_gameinfo", "-window"])
print("[Python] MAME launched. Waiting up to 5 seconds for Lua signal...")

try:
    # 4. Attempt to accept the connection
    conn, addr = server_socket.accept()
    
    # 5. Read the confirmation message
    message = conn.recv(1024).decode('utf-8').strip()
    print(f"\n[SUCCESS] Connection Verified! Lua sent: '{message}'\n")
    conn.close()

except socket.timeout:
    # 6. The Kill Switch Activates Here
    print("\n[TIMEOUT KILL SWITCH] Lua script failed to connect within 5 seconds!")
    print("[Python] Force-terminating MAME process to prevent a hang...")

finally:
    # 7. Always clean up resources and ensure MAME is dead
    server_socket.close()
    if mame_process.poll() is None:  # If MAME is still running, kill it
        mame_process.terminate()
        mame_process.wait()
    print("[Python] Execution finished and cleaned up safely.")
Use code with caution.How this works under the hood:Normal Behavior: If MAME boots and Lua connects in 1 second, the accept() call succeeds immediately, bypasses the timeout, and prints the success message.Failure Behavior (The Kill Switch): If MAME crashes, or if the Lua script has a typo and fails to run, the 5-second timer expires. Python enters the except socket.timeout: block, outputs the warning, and the finally: block executes to forcefully close the MAME window and release the network port.If you test this script, let me know:Does it successfully catch the PING when everything goes right?If you intentionally rename the Lua script to break it, does the kill switch trigger as expected?User: sweet!AI: Awesome! Getting that first reliable connection and building in a solid safety net is a huge milestone for any automation or state-extraction project. Your pipeline is now structurally sound.Now that you have a verified, bulletproof communication link that cleanly handles connection queuing and failure timeouts, you have a solid foundation to build upon.Whenever you are ready to take the next steps, we can look into:Finding the exact memory hex addresses for your specific game.Upgrading the text message to a structured JSON or frame-by-frame data stream.Passing inputs or commands backwards from Python to MAME to control the game.Let me know how your testing goes or what you want to tackle next!