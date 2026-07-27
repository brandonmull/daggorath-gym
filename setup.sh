#!/bin/bash
# MAME and Lua Environment Setup Script

# ===== Configuration =====
# --- Project ---
PROJECT_DIR="$(pwd)"
EMULATION_DIR="$PROJECT_DIR/emulation"
# --- MAME ---
MAME_DIR="/usr/share/games/mame"
DAGGORATH_NAME="daggorath"
DAGGORATH_DESC="Dungeons of Daggorath (Shield Fix) (Aaron Oliver)"
DAGGORATH_ROM="Dungeons of Daggorath (shield fix).rom"
DAGGORATH_ROM_SIZE="8192"
DAGGORATH_ROM_CRC="c985282a"
DAGGORATH_ROM_SHA1="9119ac4fa30b4b37da8619e6413c7fa01a39d6c4"
DAGGORATH_INSERT_AFTER="dagorath"

echo "Setting up environment for workspace: $PROJECT_DIR"
echo "  MAME directory: $MAME_DIR"

debug_mame_config() {
    echo "===== DEBUGGING MAME CONFIGURATION ====="

    local mame_version
    mame_version=$(mame -help | grep "MAME v" | head -1)
    echo "MAME version: $mame_version"

    echo "MAME default paths:"
    mame -showconfig | grep path

    echo "Checking if coco3 driver is available:"
    mame -listdevices coco3 | head

    echo "Checking software lists for daggorath:"
    mame -listsoftware | grep -i daggorath

    echo "Checking hash directory:"
    if [ -d "$MAME_DIR/hash" ]; then
        echo "System hash directory exists"
        echo "Files in hash directory:"
        ls -la "$MAME_DIR/hash"

        if [ -f "$MAME_DIR/hash/coco_cart.xml" ]; then
            echo "coco_cart.xml exists"
            echo "Entries in coco_cart.xml:"
            grep -A 5 -B 1 "daggorath" "$MAME_DIR/hash/coco_cart.xml"
        else
            echo "WARNING: coco_cart.xml not found in hash directory"
        fi
    else
        echo "WARNING: System hash directory not found"
    fi

    echo "========================================="
}

install_dependencies() {
    echo "Installing required packages..."
    sudo apt update
    sudo apt install -y mame

    echo "Checking for Python installation..."
    if ! command -v python3 &> /dev/null; then
        echo "Python 3 not found. Installing Python..."
        sudo apt install -y python3 python3-pip python3-venv
    else
        echo "Python 3 is already installed: $(python3 --version)"
    fi
}

check_mame_permissions() {
    if [ -w "$MAME_DIR/roms" ]; then
        echo "You have write access to $MAME_DIR/roms"
    else
        echo "WARNING: You don't have write access to $MAME_DIR/roms"
        echo "You may need to use sudo to copy ROMs or modify permissions"
    fi

    if [ -w "$MAME_DIR/hash" ]; then
        echo "You have write access to $MAME_DIR/hash"
    else
        echo "WARNING: You don't have write access to $MAME_DIR/hash"
        echo "You may need to use sudo to copy hash files or modify permissions"
    fi
}

copy_mame_roms() {
    echo "Setting up ROMs directory at $MAME_DIR/roms..."

    if [ -f "$EMULATION_DIR/roms/daggorath.zip" ]; then
        echo "Found daggorath.zip in workspace, copying to $MAME_DIR/roms..."
        sudo cp "$EMULATION_DIR/roms/daggorath.zip" "$MAME_DIR/roms/daggorath.zip"
        echo "daggorath.zip installed to $MAME_DIR/roms"
    else
        echo "daggorath.zip not found in $EMULATION_DIR/roms"
        echo "Checking for other ROMs..."
    fi

    if [ -d "$EMULATION_DIR/roms" ]; then
        echo "Found ROMs directory in workspace, copying other ROMs to $MAME_DIR/roms..."
        for rom in "$EMULATION_DIR/roms/"*.zip; do
            if [ -f "$rom" ] && [ "$(basename "$rom")" != "daggorath.zip" ]; then
                sudo cp "$rom" "$MAME_DIR/roms/"
                echo "Copied $(basename "$rom") to $MAME_DIR/roms"
            fi
        done
        echo "ROMs installed to $MAME_DIR/roms"
    else
        echo "No ROMs directory found in workspace."
        echo "Please ensure your ROMs (including daggorath.zip and coco3.zip) are placed in $MAME_DIR/roms"
    fi
}

link_mame_plugins() {
    echo "Linking Lua scripts to MAME plugins..."
    if [ -d "$EMULATION_DIR" ] && [ "$(ls -A "$EMULATION_DIR" | grep -E '\.lua$')" ]; then
        sudo mkdir -p "$MAME_DIR/plugins"
        for lua_file in "$EMULATION_DIR/"*.lua; do
            if [ -f "$lua_file" ]; then
                sudo cp "$lua_file" "$MAME_DIR/plugins/"
                echo "Copied $(basename "$lua_file") to $MAME_DIR/plugins/"
            fi
        done
    else
        echo "No Lua scripts found in $EMULATION_DIR"
    fi
}

verify_mame_roms() {
    echo ""
    echo "Verifying ROMs with MAME..."
    if command -v mame &> /dev/null; then
        echo "Running ROM verification for installed ROMs..."
        for rom in coco3 daggorath; do
            echo "Verifying ROM: $rom"
            mame -verifyroms $rom
        done
    else
        echo "MAME not found in PATH. Cannot verify ROMs."
    fi

    echo ""
    echo "Checking for Daggorath ROM..."
    if [ -f "$MAME_DIR/roms/daggorath.zip" ]; then
        echo "Found daggorath.zip in $MAME_DIR/roms"
    else
        echo "WARNING: daggorath.zip not found in $MAME_DIR/roms!"
        echo "Please ensure you have the ROM file correctly named and placed in the MAME roms directory."
        echo "Expected location: $MAME_DIR/roms/daggorath.zip"
    fi
}

ensure_mame_softlist_entry() {
    local softlist_file="$1"
    local entry_name="$2"
    local entry_desc="$3"
    local rom_name="$4"
    local rom_size="$5"
    local rom_crc="$6"
    local rom_sha1="$7"
    local insert_after="$8"

    echo ""
    echo "Checking for $entry_name in softlist..."

    if ! command -v xmlstarlet &> /dev/null; then
        echo "xmlstarlet not found, installing..."
        sudo apt update && sudo apt install -y xmlstarlet
    fi

    if [ -f "$softlist_file" ]; then
        echo "System softlist exists, checking for '$entry_name' entry..."

        if xmlstarlet sel -t -v "//software[@name='$entry_name']" "$softlist_file" &> /dev/null; then
            echo "Entry for '$entry_name' already exists, no update needed."
        else
            echo "No entry for '$entry_name' found, adding it."

            sudo cp "$softlist_file" "${softlist_file}.bak"
            echo "Backed up softlist to ${softlist_file}.bak"

            if [ -n "$insert_after" ] && xmlstarlet sel -t -v "//software[@name='$insert_after']" "$softlist_file" &> /dev/null; then
                echo "Found '$insert_after' entry, will insert '$entry_name' after it..."

                local pos
                pos=$(xmlstarlet sel -t -v "count(//software[@name='$insert_after']/preceding-sibling::software) + 1" "$softlist_file")

                sudo xmlstarlet ed -L \
                    -s "//softwarelist" -t elem -n "software" -v "" \
                    -i "//software[last()]" -t attr -n "name" -v "$entry_name" \
                    -s "//software[@name='$entry_name']" -t elem -n "description" -v "$entry_desc" \
                    -s "//software[@name='$entry_name']" -t elem -n "rom" -v "" \
                    -i "//software[@name='$entry_name']/rom" -t attr -n "name" -v "$rom_name" \
                    -i "//software[@name='$entry_name']/rom" -t attr -n "size" -v "$rom_size" \
                    -i "//software[@name='$entry_name']/rom" -t attr -n "crc" -v "$rom_crc" \
                    -i "//software[@name='$entry_name']/rom" -t attr -n "sha1" -v "$rom_sha1" \
                    "$softlist_file"

                if [ "$pos" -gt 0 ]; then
                    local total
                    total=$(xmlstarlet sel -t -v "count(//software)" "$softlist_file")

                    sudo xmlstarlet ed -L \
                        -m "//software[$total]" "//software[$pos]" \
                        "$softlist_file"

                    echo "Successfully added '$entry_name' entry after '$insert_after'."
                fi
            else
                echo "Appending '$entry_name' entry at the end..."

                sudo xmlstarlet ed -L \
                    -s "//softwarelist" -t elem -n "software" -v "" \
                    -i "//software[last()]" -t attr -n "name" -v "$entry_name" \
                    -s "//software[@name='$entry_name']" -t elem -n "description" -v "$entry_desc" \
                    -s "//software[@name='$entry_name']" -t elem -n "rom" -v "" \
                    -i "//software[@name='$entry_name']/rom" -t attr -n "name" -v "$rom_name" \
                    -i "//software[@name='$entry_name']/rom" -t attr -n "size" -v "$rom_size" \
                    -i "//software[@name='$entry_name']/rom" -t attr -n "crc" -v "$rom_crc" \
                    -i "//software[@name='$entry_name']/rom" -t attr -n "sha1" -v "$rom_sha1" \
                    "$softlist_file"

                echo "Successfully added '$entry_name' entry at the end of the software list."
            fi
        fi
    else
        echo "System softlist doesn't exist."
        echo "WARNING: This script will NOT create a new softlist file."
        echo "Please ensure the file exists in $MAME_DIR/hash before running MAME with Daggorath."
    fi

    echo "Softlist entry check complete"
}

setup_pulseaudio() {
    local pulse_socket="/mnt/wslg/PulseServer"

    echo ""
    echo "===== AUDIO SETUP ====="
    if [ -n "$WSL_INTEROP" ]; then
        if [ -S "$pulse_socket" ]; then
            echo "MAME will use '-sound pulse' for audio output"
            echo "Audio will route through your Windows speakers."
        else
            echo "WSLg PulseAudio not found. Audio will be unavailable."
            echo "Use '-sound none' to run MAME without sound."
        fi
        echo "Updating SDL2 for improved audio stability..."
        sudo apt install --only-upgrade -y libsdl2-2.0-0 2>/dev/null || true
    else
        echo "Non-WSL environment. MAME will use the default ALSA backend."
        echo "Install pulseaudio for the Pulse backend:"
        echo "    sudo apt install -y pulseaudio"
    fi
    echo "========================="
}

# ===== Run =====
debug_mame_config
install_dependencies
check_mame_permissions
copy_mame_roms
link_mame_plugins
echo ""
echo "Setup complete!"
echo "To activate your virtual environment, run: source $PROJECT_DIR/.venv/bin/activate"
echo "To test MAME with Lua, run: mame -console"
echo "ROMs are installed at: $MAME_DIR/roms"
echo "Hash files should be placed at: $MAME_DIR/hash"
verify_mame_roms
ensure_mame_softlist_entry \
    "$MAME_DIR/hash/coco_cart.xml" \
    "$DAGGORATH_NAME" \
    "$DAGGORATH_DESC" \
    "$DAGGORATH_ROM" \
    "$DAGGORATH_ROM_SIZE" \
    "$DAGGORATH_ROM_CRC" \
    "$DAGGORATH_ROM_SHA1" \
    "$DAGGORATH_INSERT_AFTER"
setup_pulseaudio