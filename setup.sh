#!/bin/bash
# MAME and Lua Environment Setup Script

# Use current directory instead of absolute path
WORKSPACE="$(pwd)"
echo "Setting up environment for workspace: $WORKSPACE"

# Install required packages
echo "Installing required packages..."
sudo apt update
sudo apt install -y lua5.3 liblua5.3-dev build-essential libreadline-dev mame luarocks lua-socket

# Create MAME directories
echo "Creating MAME directories..."
MAME_DIRS="roms hash samples artwork ctrlr ini fonts cheat crosshair plugins language software bgfx cfg nvram inp sta snap diff comments"

# Function to check and create directory
check_create_dir() {
  local dir="$1"
  if [ ! -d "$dir" ]; then
    echo "Creating $dir..."
    mkdir -p "$dir"
    if [ ! -d "$dir" ]; then
      echo "Error: Failed to create $dir. Please check permissions."
      return 1
    fi
  else
    echo "$dir already exists."
  fi
  return 0
}

# Create ~/.mame if it doesn't exist
if ! check_create_dir ~/.mame; then
  echo "Error: Unable to create main MAME directory."
  exit 1
fi

# Create each subdirectory and verify
for dir in $MAME_DIRS; do
  if ! check_create_dir ~/.mame/$dir; then
    echo "Error: Failed to create ~/.mame/$dir directory."
    exit 1
  fi
done
echo "MAME directories created successfully."

# Copy and configure MAME ini
echo "Configuring MAME..."
if [ ! -f ~/.mame/mame.ini ]; then
  cp /etc/mame/mame.ini ~/.mame/
  
  # Update paths in mame.ini
  sed -i 's|^rompath.*|rompath                   $HOME/.mame/roms;/usr/local/share/games/mame/roms;/usr/share/games/mame/roms|' ~/.mame/mame.ini
  sed -i 's|^hashpath.*|hashpath                  $HOME/.mame/hash;/usr/local/share/games/mame/hash;/usr/share/games/mame/hash|' ~/.mame/mame.ini
  sed -i 's|^samplepath.*|samplepath                $HOME/.mame/samples;/usr/local/share/games/mame/samples;/usr/share/games/mame/samples|' ~/.mame/mame.ini
  sed -i 's|^artpath.*|artpath                   $HOME/.mame/artwork;/usr/local/share/games/mame/artwork;/usr/share/games/mame/artwork|' ~/.mame/mame.ini
  sed -i 's|^ctrlrpath.*|ctrlrpath                 $HOME/.mame/ctrlr;/usr/local/share/games/mame/ctrlr;/usr/share/games/mame/ctrlr|' ~/.mame/mame.ini
  sed -i 's|^inipath.*|inipath                   $HOME/.mame/ini;/usr/local/etc/mame;/etc/mame|' ~/.mame/mame.ini
  sed -i 's|^fontpath.*|fontpath                  $HOME/.mame/fonts;/usr/local/share/games/mame/fonts;/usr/share/games/mame/fonts|' ~/.mame/mame.ini
  sed -i 's|^cheatpath.*|cheatpath                 $HOME/.mame/cheat;/usr/local/share/games/mame/cheat;/usr/share/games/mame/cheat|' ~/.mame/mame.ini
  sed -i 's|^crosshairpath.*|crosshairpath             $HOME/.mame/crosshair;/usr/local/share/games/mame/crosshair;/usr/share/games/mame/crosshair|' ~/.mame/mame.ini
  sed -i 's|^pluginspath.*|pluginspath               $HOME/.mame/plugins;/usr/local/share/games/mame/plugins;/usr/share/games/mame/plugins|' ~/.mame/mame.ini
  sed -i 's|^languagepath.*|languagepath              $HOME/.mame/language;/usr/local/share/games/mame/language;/usr/share/games/mame/language|' ~/.mame/mame.ini
  sed -i 's|^swpath.*|swpath                    $HOME/.mame/software;/usr/local/share/games/mame/software;/usr/share/games/mame/software|' ~/.mame/mame.ini
  sed -i 's|^bgfx_path.*|bgfx_path                 $HOME/.mame/bgfx;/usr/local/share/games/mame/bgfx;/usr/share/games/mame/bgfx|' ~/.mame/mame.ini
fi

# Install ROMs to ~/.mame/roms
echo "Setting up ROMs directory at $HOME/.mame/roms..."

# Check for ROMs directory in workspace
if [ -d "$WORKSPACE/roms" ]; then
  echo "Found ROMs directory in workspace, copying to ~/.mame/roms..."
  cp -r "$WORKSPACE/roms/"* ~/.mame/roms/ 2>/dev/null || true
  echo "ROMs installed to $HOME/.mame/roms"
else
  echo "No ROMs directory found in workspace. Please ensure your ROMs (including daggorath.zip and coco3.zip) are placed in $HOME/.mame/roms"
fi

# Create src/emu directory in workspace if it doesn't exist
echo "Setting up Lua directories..."
mkdir -p "$WORKSPACE/src/emu"
mkdir -p "$WORKSPACE/env"

# Install Lua packages to workspace env directory
echo "Installing Lua packages..."
cd "$WORKSPACE"
luarocks install --tree="$WORKSPACE/env" luasocket
luarocks install --tree="$WORKSPACE/env" luafilesystem

# Link Lua scripts to MAME plugins directory
echo "Linking Lua scripts to MAME plugins..."
if [ -d "$WORKSPACE/src/emu" ] && [ "$(ls -A "$WORKSPACE/src/emu")" ]; then
  ln -sf "$WORKSPACE/src/emu/"* ~/.mame/plugins/
else
  echo "No Lua scripts found in $WORKSPACE/src/emu"
fi

# Update virtual environment activate script
echo "Updating virtual environment..."
if [ -f "$WORKSPACE/env/bin/activate" ]; then
  # Check if LUA_PATH is already in activate script
  if ! grep -q "LUA_PATH" "$WORKSPACE/env/bin/activate"; then
    echo "
# Lua environment
export LUA_PATH=\"$WORKSPACE/env/share/lua/5.3/?.lua;$WORKSPACE/env/share/lua/5.3/?/init.lua;$WORKSPACE/src/emu/?.lua;$WORKSPACE/src/emu/?/init.lua;;\"
export LUA_CPATH=\"$WORKSPACE/env/lib/lua/5.3/?.so;;\"
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
echo "ROMs are installed at: $HOME/.mame/roms"

# Set up Lua environment variables using ~ for home directory
export LUA_PATH="~/.mame/plugins/share/lua/5.3/?.lua;~/.mame/plugins/share/lua/5.3/?/init.lua;./?.lua;./?/init.lua"
export LUA_CPATH="~/.mame/plugins/lib/lua/5.3/?.so;~/.mame/plugins/lib/lua/5.3/?/?.so;./?.so"
export PATH="~/.mame/plugins/bin:$PATH"

# Print the configured paths for verification
echo "Lua module path: $LUA_PATH"
echo "Lua C library path: $LUA_CPATH"
echo "Updated PATH: $PATH"
echo "MAME ROM path: $HOME/.mame/roms"

# You can add any additional setup steps below