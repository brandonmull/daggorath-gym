#!/bin/bash
# Script to fix the structure of the Daggorath ROM zip file

# Path to the MAME ROMs directory
MAME_ROMS_DIR="/usr/share/games/mame/roms"

# Check if the ROM file exists
if [ ! -f "$MAME_ROMS_DIR/daggorath.zip" ]; then
    echo "ERROR: daggorath.zip not found in $MAME_ROMS_DIR!"
    echo "Please ensure the ROM file is correctly named and placed in the MAME roms directory."
    exit 1
fi

# Create a temporary directory
TEMP_DIR=$(mktemp -d)
echo "Extracting daggorath.zip to $TEMP_DIR..."

# Extract the ROM
unzip -q "$MAME_ROMS_DIR/daggorath.zip" -d "$TEMP_DIR"

# List all extracted files
echo "Files extracted from daggorath.zip:"
find "$TEMP_DIR" -type f | while read -r file; do
    echo "  $(basename "$file") ($(stat -c%s "$file") bytes)"
done

# The expected ROM filename for Dungeons of Daggorath
EXPECTED_ROM_NAME="Dungeons of Daggorath (shield fix).rom"

# Find all ROM files in the extracted directory (including subdirectories)
ROM_FILES=$(find "$TEMP_DIR" -type f -name "*.rom" -o -name "*.bin")

if [ -z "$ROM_FILES" ]; then
    echo "No ROM files found with .rom or .bin extension. Searching for all files..."
    ROM_FILES=$(find "$TEMP_DIR" -type f)
fi

if [ -z "$ROM_FILES" ]; then
    echo "No files found in the ROM archive."
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Create a new zip file with the correct structure
FIXED_ZIP=$(mktemp)
echo "Creating fixed daggorath.zip with correct structure..."

# Copy the first ROM file found to the correct name
ROM_FILE=$(echo "$ROM_FILES" | head -1)
cp "$ROM_FILE" "$TEMP_DIR/$EXPECTED_ROM_NAME"

# Create the fixed zip file with the ROM directly in the root
cd "$TEMP_DIR"
zip -j "$FIXED_ZIP" "$EXPECTED_ROM_NAME"

# Backup the original file
sudo cp "$MAME_ROMS_DIR/daggorath.zip" "$MAME_ROMS_DIR/daggorath.zip.bak"
echo "Original daggorath.zip backed up to $MAME_ROMS_DIR/daggorath.zip.bak"

# Copy the fixed zip to the original location
sudo cp "$FIXED_ZIP" "$MAME_ROMS_DIR/daggorath.zip"
echo "Fixed daggorath.zip installed to $MAME_ROMS_DIR/daggorath.zip"

# Clean up
rm "$FIXED_ZIP"
rm -rf "$TEMP_DIR"

echo "ZIP file structure fixed. The ROM should now be directly in the root of the zip file with the correct name."
echo "Try running: mame -verifyroms daggorath"

exit 0 