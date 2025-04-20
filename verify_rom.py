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
        # Read the file in chunks to handle large files
        crc = 0
        for chunk in iter(lambda: f.read(8192), b''):
            crc = zlib.crc32(chunk, crc)
        return "%08x" % (crc & 0xFFFFFFFF)

def calculate_sha1(file_path):
    """Calculate SHA1 hash of a file"""
    sha1 = hashlib.sha1()
    with open(file_path, 'rb') as f:
        # Read the file in chunks
        for chunk in iter(lambda: f.read(8192), b''):
            sha1.update(chunk)
    return sha1.hexdigest()

def extract_and_verify_rom(zip_path, xml_path, temp_dir='temp'):
    """Extract the ROM and verify against expected values from XML"""
    # Create temp directory if it doesn't exist
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    
    # Parse the XML to get expected values
    tree = ET.parse(xml_path)
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
        return False
    
    # Extract ROM from zip
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        file_list = zip_ref.namelist()
        print(f"Files in the ZIP archive: {file_list}")
        
        # Extract all files
        zip_ref.extractall(temp_dir)
    
    # Verify each extracted file against expected values
    matched_any = False
    
    for root_dir, _, files in os.walk(temp_dir):
        for filename in files:
            file_path = os.path.join(root_dir, filename)
            file_size = os.path.getsize(file_path)
            
            # Try to match with any expected ROM
            for expected_name, expected_data in expected_values.items():
                if file_size == expected_data['size']:
                    print(f"Checking {filename} (size matches {expected_name})...")
                    
                    # Calculate actual hashes
                    actual_crc = calculate_crc32(file_path)
                    actual_sha1 = calculate_sha1(file_path)
                    
                    print(f"  Expected CRC: {expected_data['crc']}")
                    print(f"  Actual CRC:   {actual_crc}")
                    print(f"  CRC Match:    {expected_data['crc'] == actual_crc}")
                    
                    print(f"  Expected SHA1: {expected_data['sha1']}")
                    print(f"  Actual SHA1:   {actual_sha1}")
                    print(f"  SHA1 Match:    {expected_data['sha1'] == actual_sha1}")
                    
                    if expected_data['crc'] == actual_crc and expected_data['sha1'] == actual_sha1:
                        print(f"SUCCESS: {filename} matches the expected ROM '{expected_name}'")
                        matched_any = True
                    else:
                        print(f"MISMATCH: {filename} has different hash values than expected for '{expected_name}'")
    
    if not matched_any:
        print("WARNING: No files in the ZIP archive matched the expected hash values.")
    
    return matched_any

if __name__ == '__main__':
    rom_zip = 'emu/roms/daggorath.zip'
    xml_file = '/usr/share/games/mame/hash/coco_cart.xml'
    
    if len(sys.argv) > 1:
        rom_zip = sys.argv[1]
    if len(sys.argv) > 2:
        xml_file = sys.argv[2]
    
    print(f"Verifying ROM: {rom_zip}")
    print(f"Using XML file: {xml_file}")
    
    if not os.path.exists(rom_zip):
        print(f"ERROR: ROM file not found: {rom_zip}")
        sys.exit(1)
    
    if not os.path.exists(xml_file):
        print(f"ERROR: XML file not found: {xml_file}")
        sys.exit(1)
    
    success = extract_and_verify_rom(rom_zip, xml_file)
    if success:
        print("\nVerification PASSED: The ROM matches the expected values.")
        sys.exit(0)
    else:
        print("\nVerification FAILED: The ROM does not match the expected values.")
        sys.exit(1) 