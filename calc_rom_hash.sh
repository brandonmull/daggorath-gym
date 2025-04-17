#!/bin/bash
# ROM Hash Calculator Script
# This script extracts a ROM file and calculates its hash values

# Check if a ROM file was provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 path/to/your/rom.zip [output_xml_file]"
    echo "Example: $0 /usr/share/games/mame/roms/daggorath.zip"
    exit 1
fi

ROM_ZIP="$1"
OUTPUT_XML="${2:-rom_hash.xml}"

# Check if the ROM file exists
if [ ! -f "$ROM_ZIP" ]; then
    echo "ERROR: ROM file $ROM_ZIP not found!"
    exit 1
fi

# Create a temporary directory for extraction
TEMP_DIR=$(mktemp -d)
echo "Extracting $ROM_ZIP to $TEMP_DIR..."

# Extract the ROM
unzip -q "$ROM_ZIP" -d "$TEMP_DIR"

# List all extracted files
echo "Files extracted from $ROM_ZIP:"
find "$TEMP_DIR" -type f | while read -r file; do
    echo "  $(basename "$file") ($(stat -c%s "$file") bytes)"
done

# Find all ROM files in the extracted directory (including subdirectories)
echo -e "\nSearching for ROM files..."
ROM_FILES=$(find "$TEMP_DIR" -type f -name "*.rom" -o -name "*.bin")

if [ -z "$ROM_FILES" ]; then
    echo "No ROM files found with .rom or .bin extension. Searching for all files..."
    ROM_FILES=$(find "$TEMP_DIR" -type f)
fi

# Process each ROM file found
echo -e "\nROM file information:"
echo "======================="

find "$TEMP_DIR" -type f | while read -r ROM_FILE; do
    ROM_NAME=$(basename "$ROM_FILE")
    ROM_SIZE=$(stat -c%s "$ROM_FILE")
    
    echo "File: $ROM_NAME"
    echo "Size: $ROM_SIZE bytes"
    
    # Calculate CRC32
    CRC32=$(python3 -c "import zlib; import sys; print(format(zlib.crc32(open('$ROM_FILE','rb').read()) & 0xFFFFFFFF, '08x'))" 2>/dev/null)
    if [ -n "$CRC32" ]; then
        echo "CRC32: $CRC32"
    else
        echo "Error calculating CRC32"
    fi
    
    # Calculate SHA1
    if command -v sha1sum &> /dev/null; then
        SHA1=$(sha1sum "$ROM_FILE" | cut -d' ' -f1)
        echo "SHA1: $SHA1"
    else
        echo "SHA1 utility not found"
    fi
    
    # Add to XML
    cat >> "$OUTPUT_XML" << EOF
<!-- ROM Hash Information -->
<softwarelist name="coco_cart" description="Tandy Radio Shack Color Computer cartridges">
    <software name="daggorath">
        <description>Dungeons of Daggorath</description>
        <rom name="$ROM_NAME" size="$ROM_SIZE" crc="$CRC32" sha1="$SHA1" />
    </software>
</softwarelist>
EOF
    
    echo "XML entry written to $OUTPUT_XML"
    echo ""
done

# Expected values
echo "Expected hash values for Dungeons of Daggorath:"
echo "Filename: \"Dungeons of Daggorath (shield fix).rom\""
echo "Size: 8192 bytes"
echo "CRC: c985282a"
echo "SHA1: 9119ac4fa30b4b37da8619e6413c7fa01a39d6c4"

# Clean up
rm -rf "$TEMP_DIR"
echo "Temporary files cleaned up."
echo "Script completed."

exit 0 