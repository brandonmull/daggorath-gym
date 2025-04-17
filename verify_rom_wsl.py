#!/usr/bin/env python3

import os
import zipfile
import hashlib
import xml.etree.ElementTree as ET
import zlib
import sys

def calculate_crc32(file_path):
    """Calculate CRC32 of a file"""
    with open(file_path, 'rb') as f:
        buffer = f.read()
        crc = zlib.crc32(buffer) & 0xFFFFFFFF
        return "%08x" % crc

def calculate_sha1(file_path):
    """Calculate SHA1 hash of a file"""
    sha1 = hashlib.sha1()
    with open(file_path, 'rb') as f:
        buffer = f.read()
        sha1.update(buffer)
    return sha1.hexdigest()

# Paths
rom_zip = 'emu/roms/daggorath.zip'
xml_file = 'emu/hash/daggorath_cart.xml'
temp_dir = 'temp'

print(f"Verifying ROM: {rom_zip}")
print(f"Using XML file: {xml_file}")

# Check files exist
if not os.path.exists(rom_zip):
    print(f"ERROR: ROM file not found: {rom_zip}")
    sys.exit(1)

if not os.path.exists(xml_file):
    print(f"ERROR: XML file not found: {xml_file}")
    sys.exit(1)

# Create temp directory if it doesn't exist
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)

# Parse the XML to get expected values
tree = ET.parse(xml_file)
root = tree.getroot()

expected_values = {}
for software in root.findall('.//software'):
    for rom in software.findall('.//rom'):
        rom_name = rom.get('name')
        expected_values[rom_name] = {
            'size': int(rom.get('size')),
            'crc': rom.get('crc').lower(),
            'sha1': rom.get('sha1').lower()
        }

if not expected_values:
    print("No ROM information found in the XML file.")
    sys.exit(1)

print(f"Expected ROM values from XML:")
for name, values in expected_values.items():
    print(f"  ROM: {name}")
    print(f"    Size: {values['size']} bytes")
    print(f"    CRC:  {values['crc']}")
    print(f"    SHA1: {values['sha1']}")

# Extract ROM from zip
with zipfile.ZipFile(rom_zip, 'r') as zip_ref:
    file_list = zip_ref.namelist()
    print(f"\nFiles in the ZIP archive: {file_list}")
    
    # Extract all files
    zip_ref.extractall(temp_dir)

# Verify each extracted file against expected values
matched_any = False

for root_dir, _, files in os.walk(temp_dir):
    for filename in files:
        file_path = os.path.join(root_dir, filename)
        file_size = os.path.getsize(file_path)
        
        print(f"\nChecking {filename}...")
        print(f"  Size: {file_size} bytes")
        
        # Calculate actual hashes
        actual_crc = calculate_crc32(file_path)
        actual_sha1 = calculate_sha1(file_path)
        
        print(f"  Actual CRC:  {actual_crc}")
        print(f"  Actual SHA1: {actual_sha1}")
        
        # Try to match with any expected ROM
        for expected_name, expected_data in expected_values.items():
            if file_size == expected_data['size']:
                print(f"  Size matches expected ROM '{expected_name}'")
                
                print(f"  Expected CRC:  {expected_data['crc']}")
                print(f"  CRC Match:     {expected_data['crc'] == actual_crc}")
                
                print(f"  Expected SHA1: {expected_data['sha1']}")
                print(f"  SHA1 Match:    {expected_data['sha1'] == actual_sha1}")
                
                if expected_data['crc'] == actual_crc and expected_data['sha1'] == actual_sha1:
                    print(f"  SUCCESS: {filename} matches the expected ROM '{expected_name}'")
                    matched_any = True
                else:
                    print(f"  MISMATCH: {filename} has different hash values than expected for '{expected_name}'")

if not matched_any:
    print("\nWARNING: No files in the ZIP archive matched the expected hash values.")
    sys.exit(1)
else:
    print("\nVerification PASSED: At least one ROM matches the expected values.")
    sys.exit(0) 