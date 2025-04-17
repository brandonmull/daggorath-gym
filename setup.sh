#!/bin/bash
# MAME and Lua Environment Setup Script

# Use current directory instead of absolute path
WORKSPACE="$(pwd)"
echo "Setting up environment for workspace: $WORKSPACE"

# Debug MAME configuration
debug_mame_config() {
  echo "===== DEBUGGING MAME CONFIGURATION ====="
  
  # Check MAME version
  MAME_VERSION=$(mame -help | grep "MAME v" | head -1)
  echo "MAME version: $MAME_VERSION"
  
  # Check MAME default paths
  echo "MAME default paths:"
  mame -showconfig | grep path
  
  # Check if coco3 driver is available
  echo "Checking if coco3 driver is available:"
  mame -listdevices coco3 | head
  
  # Check if daggorath is in software lists
  echo "Checking software lists for daggorath:"
  mame -listsoftware | grep -i daggorath
  
  # Check hash path existence
  echo "Checking hash directory:"
  if [ -d "/usr/share/games/mame/hash" ]; then
    echo "System hash directory exists"
    echo "Files in hash directory:"
    ls -la /usr/share/games/mame/hash
    
    # Check for coco_cart.xml specifically
    if [ -f "/usr/share/games/mame/hash/coco_cart.xml" ]; then
      echo "coco_cart.xml exists"
      echo "Entries in coco_cart.xml:"
      grep -A 5 -B 1 "daggorath" /usr/share/games/mame/hash/coco_cart.xml
    else
      echo "WARNING: coco_cart.xml not found in hash directory"
    fi
  else
    echo "WARNING: System hash directory not found"
  fi
  
  echo "========================================="
}

# Run MAME configuration debugging
debug_mame_config

# Install required packages
echo "Installing required packages..."
sudo apt update
sudo apt install -y lua5.3 liblua5.3-dev build-essential libreadline-dev mame luarocks lua-socket

# Check for Python installation
echo "Checking for Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found. Installing Python..."
    sudo apt install -y python3 python3-pip python3-venv
else
    echo "Python 3 is already installed: $(python3 --version)"
fi

# Define paths from paths.lua
MAME_DIR="/usr/share/games/mame"
MAME_ROMS_DIR="$MAME_DIR/roms"
MAME_HASH_DIR="$MAME_DIR/hash"
LUA_DIR="/usr/local/share/lua/5.3"
LUA_C_DIR="/usr/local/lib/lua/5.3"
SOCKET_HOST="127.0.0.1"
SOCKET_PORT="15000"

echo "Using paths from paths.lua:"
echo "  MAME directory: $MAME_DIR"
echo "  MAME ROMs directory: $MAME_ROMS_DIR"
echo "  MAME hash directory: $MAME_HASH_DIR"
echo "  Lua directory: $LUA_DIR"
echo "  Lua C directory: $LUA_C_DIR"
echo "  Socket host: $SOCKET_HOST"
echo "  Socket port: $SOCKET_PORT"

# Check ROMs directory access
if [ -w "$MAME_ROMS_DIR" ]; then
  echo "You have write access to $MAME_ROMS_DIR"
else
  echo "WARNING: You don't have write access to $MAME_ROMS_DIR"
  echo "You may need to use sudo to copy ROMs or modify permissions"
fi

# Check hash directory access
if [ -w "$MAME_HASH_DIR" ]; then
  echo "You have write access to $MAME_HASH_DIR"
else
  echo "WARNING: You don't have write access to $MAME_HASH_DIR"
  echo "You may need to use sudo to copy hash files or modify permissions"
fi

# Copy ROMs to system MAME ROM directory
echo "Setting up ROMs directory at $MAME_ROMS_DIR..."

# Specifically check for daggorath ROM in emu/roms
if [ -f "$WORKSPACE/emu/roms/daggorath.zip" ]; then
  echo "Found daggorath.zip in workspace, copying to $MAME_ROMS_DIR..."
  sudo cp "$WORKSPACE/emu/roms/daggorath.zip" "$MAME_ROMS_DIR/daggorath.zip"
  echo "daggorath.zip installed to $MAME_ROMS_DIR"
else
  echo "daggorath.zip not found in $WORKSPACE/emu/roms"
  echo "Checking for other ROMs..."
fi

# Check for ROMs directory in workspace
if [ -d "$WORKSPACE/emu/roms" ]; then
  echo "Found ROMs directory in workspace, copying other ROMs to $MAME_ROMS_DIR..."
  for rom in "$WORKSPACE/emu/roms/"*.zip; do
    if [ -f "$rom" ] && [ "$(basename "$rom")" != "daggorath.zip" ]; then
      sudo cp "$rom" "$MAME_ROMS_DIR/"
      echo "Copied $(basename "$rom") to $MAME_ROMS_DIR"
    fi
  done
  echo "ROMs installed to $MAME_ROMS_DIR"
else
  echo "No ROMs directory found in workspace. Please ensure your ROMs (including daggorath.zip and coco3.zip) are placed in $MAME_ROMS_DIR"
fi

# Link Lua scripts to MAME plugins directory
echo "Linking Lua scripts to MAME plugins..."
if [ -d "$WORKSPACE/emu" ] && [ "$(ls -A "$WORKSPACE/emu" | grep -E '\.lua$')" ]; then
  sudo mkdir -p "$MAME_DIR/plugins"
  for lua_file in "$WORKSPACE/emu/"*.lua; do
    if [ -f "$lua_file" ]; then
      sudo cp "$lua_file" "$MAME_DIR/plugins/"
      echo "Copied $(basename "$lua_file") to $MAME_DIR/plugins/"
    fi
  done
else
  echo "No Lua scripts found in $WORKSPACE/emu"
fi

# Create env directory in workspace if it doesn't exist
echo "Setting up Lua directories..."
mkdir -p "$WORKSPACE/env"

# Install Lua packages to workspace env directory
echo "Installing Lua packages..."
cd "$WORKSPACE"
luarocks install --tree="$WORKSPACE/env" luasocket
luarocks install --tree="$WORKSPACE/env" luafilesystem

# Update virtual environment activate script with paths from paths.lua
echo "Updating virtual environment..."
if [ -f "$WORKSPACE/env/bin/activate" ]; then
  # Check if LUA_PATH is already in activate script
  if ! grep -q "LUA_PATH" "$WORKSPACE/env/bin/activate"; then
    echo "
# Lua environment
export LUA_PATH=\"$WORKSPACE/env/share/lua/5.3/?.lua;$WORKSPACE/env/share/lua/5.3/?/init.lua;$WORKSPACE/emu/?.lua;$WORKSPACE/emu/?/init.lua;$LUA_DIR/?.lua;$LUA_DIR/?/init.lua;;\"
export LUA_CPATH=\"$WORKSPACE/env/lib/lua/5.3/?.so;$LUA_C_DIR/?.so;$LUA_C_DIR/?/core.so;;\"
" >> "$WORKSPACE/env/bin/activate"

    # Add to deactivate function
    sed -i '/deactivate () {/a \
    # Reset Lua environment\
    unset LUA_PATH\
    unset LUA_CPATH' "$WORKSPACE/env/bin/activate"
  fi
fi

echo "Setup complete!"
echo "To activate your virtual environment, run: source $WORKSPACE/env/bin/activate"
echo "To test MAME with Lua, run: mame -console"
echo "ROMs are installed at: $MAME_ROMS_DIR"
echo "Hash files should be placed at: $MAME_HASH_DIR"

# Set up Lua environment variables using paths from paths.lua
export LUA_PATH="$MAME_DIR/plugins/share/lua/5.3/?.lua;$MAME_DIR/plugins/share/lua/5.3/?/init.lua;$LUA_DIR/?.lua;$LUA_DIR/?/init.lua;./?.lua;./?/init.lua"
export LUA_CPATH="$MAME_DIR/plugins/lib/lua/5.3/?.so;$MAME_DIR/plugins/lib/lua/5.3/?/?.so;$LUA_C_DIR/?.so;$LUA_C_DIR/?/core.so;./?.so"
export PATH="$MAME_DIR/plugins/bin:$PATH"

# Print the configured paths for verification
echo "Lua module path: $LUA_PATH"
echo "Lua C library path: $LUA_CPATH"
echo "Updated PATH: $PATH"
echo "MAME ROM path: $MAME_ROMS_DIR"
echo "MAME hash path: $MAME_HASH_DIR"
echo "Socket configuration: $SOCKET_HOST:$SOCKET_PORT"

# Verify ROMs
echo "Verifying ROMs with MAME..."
if command -v mame &> /dev/null; then
  # Run MAME's verification tool to check ROMs against hash files
  echo "Running ROM verification for installed ROMs..."
  
  # Specifically verify the ROMs we need
  for rom in coco3 daggorath; do
    echo "Verifying ROM: $rom"
    mame -verifyroms $rom
  done
else
  echo "MAME not found in PATH. Cannot verify ROMs."
fi

# Check specifically for the Daggorath ROM
echo ""
echo "Checking for Daggorath ROM..."
if [ -f "$MAME_ROMS_DIR/daggorath.zip" ]; then
    echo "Found daggorath.zip in $MAME_ROMS_DIR"
else
    echo "WARNING: daggorath.zip not found in $MAME_ROMS_DIR!"
    echo "Please ensure you have the ROM file correctly named and placed in the MAME roms directory."
    echo "Expected location: $MAME_ROMS_DIR/daggorath.zip"
fi

# Function to clean up unnecessary scripts
cleanup_scripts() {
    echo "===== CLEANING UP EXTRA SCRIPTS ====="
    # Move extra scripts to a backup directory
    mkdir -p .backup_scripts
    mv check_rom_mame.sh debug_mame.sh verify_rom.py verify_rom_wsl.py .backup_scripts/ 2>/dev/null
    echo "Extra scripts moved to .backup_scripts directory"
}

# You can add any additional setup steps below