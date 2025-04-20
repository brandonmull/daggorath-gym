#!/usr/bin/env python3
"""
Setup script to copy necessary MAME hash files
This prevents corruption of system-wide hash files when running with debug options
"""

import os
import shutil
import sys
from pathlib import Path

# Define source and destination paths
SYSTEM_HASH_DIR = "/usr/share/games/mame/hash"
LOCAL_HASH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hash")

# Files needed for the Daggorath environment
REQUIRED_FILES = [
    "coco_cart.xml",
]

def main():
    """Copy necessary hash files from MAME system directory"""
    # Create the hash directory if it doesn't exist
    os.makedirs(LOCAL_HASH_DIR, exist_ok=True)
    
    # Check if the system hash directory exists
    if not os.path.isdir(SYSTEM_HASH_DIR):
        print(f"Error: System hash directory not found at {SYSTEM_HASH_DIR}")
        print("You may need to manually download the hash files from:")
        print("https://github.com/mamedev/mame/tree/master/hash")
        return 1
    
    # Copy each required file
    for filename in REQUIRED_FILES:
        src_path = os.path.join(SYSTEM_HASH_DIR, filename)
        dst_path = os.path.join(LOCAL_HASH_DIR, filename)
        
        if os.path.exists(src_path):
            print(f"Copying {filename}...")
            
            # Backup existing file if present
            if os.path.exists(dst_path):
                backup_path = f"{dst_path}.bak"
                print(f"  Backing up existing file to {os.path.basename(backup_path)}")
                shutil.copy2(dst_path, backup_path)
            
            # Copy the file
            shutil.copy2(src_path, dst_path)
            print(f"  Done!")
        else:
            print(f"Warning: {filename} not found in system hash directory")
    
    print("\nSetup complete! The local hash directory has been configured.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 