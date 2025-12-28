#!/usr/bin/env python3
"""
FAT Filesystem Sorter

A command-line tool that sorts files in FAT filesystems by filename using
a safe move-to-temp-and-back approach that preserves the directory entry order.

This tool is designed for embedded devices (3D printers, MP3 players) that
read files in the order they appear in the FAT directory table.

Copyright (C) 2025 Victor Hugo Schulz

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import os
import sys
import shutil
import argparse
import logging
from pathlib import Path
from typing import List, Tuple, Optional
import tempfile
import time


class FATSorter:
    """Main class for sorting FAT filesystem directories."""
    
    def __init__(self, verbose: bool = False, log_file: Optional[str] = None):
        self.verbose = verbose
        self.setup_logging(log_file)
        
    def setup_logging(self, log_file: Optional[str]) -> None:
        """Setup logging configuration."""
        log_level = logging.INFO if self.verbose else logging.WARNING
        
        # Create logger
        self.logger = logging.getLogger('fat_sorter')
        self.logger.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            try:
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(logging.INFO)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
                self.logger.info(f"Logging to file: {log_file}")
            except Exception as e:
                self.logger.warning(f"Could not create log file {log_file}: {e}")
    
    def get_directory_entries(self, directory: Path) -> List[str]:
        """
        Get all entries (files and directories) in a directory.
        Returns them in the order they appear in the filesystem.
        """
        try:
            entries = []
            for entry in directory.iterdir():
                if not entry.name.startswith('.'):  # Skip hidden files
                    entries.append(entry.name)
            return entries
        except PermissionError:
            self.logger.error(f"Permission denied accessing directory: {directory}")
            return []
        except Exception as e:
            self.logger.error(f"Error reading directory {directory}: {e}")
            return []
    
    def is_sorted(self, entries: List[str]) -> bool:
        """Check if the list of entries is already sorted alphabetically (case-insensitive)."""
        if len(entries) <= 1:
            return True
        
        sorted_entries = sorted(entries, key=str.lower)
        is_already_sorted = entries == sorted_entries
        
        if is_already_sorted:
            self.logger.info(f"Directory already sorted: {len(entries)} entries")
        else:
            self.logger.info(f"Directory needs sorting: {len(entries)} entries")
            
        return is_already_sorted
    
    def sync_filesystem(self) -> None:
        """Force filesystem sync to ensure changes are written to disk."""
        try:
            os.sync()
            time.sleep(0.1)  # Small delay to ensure sync completes
        except:
            pass  # sync() might not be available on all systems
    
    def sort_directory_entries(self, directory: Path) -> bool:
        """
        Sort all entries in a directory using the move-to-temp-and-back method.
        Returns True if sorting was performed, False if already sorted or on error.
        """
        self.logger.info(f"Processing directory: {directory}")
        
        # Get current entries
        current_entries = self.get_directory_entries(directory)
        if not current_entries:
            self.logger.info(f"Directory is empty or inaccessible: {directory}")
            return False
        
        # Check if already sorted
        if self.is_sorted(current_entries):
            self.logger.info(f"Directory already sorted, skipping: {directory}")
            return False
        
        # Create sorted list
        sorted_entries = sorted(current_entries, key=str.lower)
        
        # Create temporary directory within the same filesystem
        temp_dir_name = f".fat_sort_temp_{int(time.time())}"
        temp_dir = directory / temp_dir_name
        
        try:
            # Create temporary directory
            temp_dir.mkdir(exist_ok=False)
            self.logger.info(f"Created temporary directory: {temp_dir}")
            
            # Phase 1: Move all entries to temp directory in sorted order
            self.logger.info("Phase 1: Moving entries to temporary location...")
            moved_entries = []
            
            for entry_name in sorted_entries:
                src_path = directory / entry_name
                dst_path = temp_dir / entry_name
                
                try:
                    if src_path.exists():
                        shutil.move(str(src_path), str(dst_path))
                        moved_entries.append(entry_name)
                        self.logger.info(f"Moved to temp: {entry_name}")
                        self.sync_filesystem()
                    else:
                        self.logger.warning(f"Entry disappeared during operation: {entry_name}")
                except Exception as e:
                    self.logger.error(f"Failed to move {entry_name} to temp: {e}")
                    # Continue with other files rather than abort
            
            # Phase 2: Move entries back from temp directory in the same order
            self.logger.info("Phase 2: Moving entries back to original location...")
            
            for entry_name in moved_entries:
                src_path = temp_dir / entry_name
                dst_path = directory / entry_name
                
                try:
                    shutil.move(str(src_path), str(dst_path))
                    self.logger.info(f"Moved back: {entry_name}")
                    self.sync_filesystem()
                except Exception as e:
                    self.logger.error(f"Failed to move {entry_name} back: {e}")
                    # This is more serious - log but continue
            
            # Clean up temporary directory
            try:
                temp_dir.rmdir()
                self.logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                self.logger.warning(f"Could not remove temporary directory {temp_dir}: {e}")
                self.logger.warning("Please remove it manually if it's empty")
            
            self.logger.info(f"Successfully sorted directory: {directory}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during sorting operation: {e}")
            self.logger.error(f"Temporary directory may still exist: {temp_dir}")
            self.logger.error("Please check the directory and clean up manually if needed")
            return False
    
    def sort_directory_recursive(self, root_directory: Path) -> Tuple[int, int]:
        """
        Recursively sort directories starting from root_directory.
        Returns tuple of (directories_processed, directories_sorted).
        """
        processed = 0
        sorted_count = 0
        
        try:
            # Sort current directory first
            processed += 1
            if self.sort_directory_entries(root_directory):
                sorted_count += 1
            
            # Then recursively sort subdirectories
            for entry in root_directory.iterdir():
                if entry.is_dir() and not entry.name.startswith('.'):
                    sub_processed, sub_sorted = self.sort_directory_recursive(entry)
                    processed += sub_processed
                    sorted_count += sub_sorted
                    
        except PermissionError:
            self.logger.error(f"Permission denied accessing: {root_directory}")
        except Exception as e:
            self.logger.error(f"Error processing directory {root_directory}: {e}")
        
        return processed, sorted_count


def main():
    """Main entry point for the command-line interface."""
    parser = argparse.ArgumentParser(
        description="Sort FAT filesystem directories by filename using safe move operations",
        epilog="""
This tool sorts files and directories by moving them to a temporary location
and back in alphabetical order, which updates the FAT directory table order.
This is useful for embedded devices that read files in filesystem order.

Examples:
  %(prog)s /media/sdcard
  %(prog)s /media/sdcard --verbose
  %(prog)s /media/sdcard --log-file sort.log
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'directory',
        type=str,
        help='Directory to sort (will be processed recursively)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '-l', '--log-file',
        type=str,
        help='Write detailed log to specified file'
    )
    
    args = parser.parse_args()
    
    # Validate directory
    target_dir = Path(args.directory).resolve()
    if not target_dir.exists():
        print(f"Error: Directory does not exist: {target_dir}", file=sys.stderr)
        sys.exit(1)
    
    if not target_dir.is_dir():
        print(f"Error: Path is not a directory: {target_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Create sorter instance
    sorter = FATSorter(verbose=args.verbose, log_file=args.log_file)
    
    print(f"FAT Sorter - Sorting directory: {target_dir}")
    if args.verbose:
        print("Verbose mode enabled")
    if args.log_file:
        print(f"Logging to: {args.log_file}")
    
    # Perform the sorting
    try:
        processed, sorted_count = sorter.sort_directory_recursive(target_dir)
        
        print(f"\nOperation completed:")
        print(f"  Directories processed: {processed}")
        print(f"  Directories sorted: {sorted_count}")
        print(f"  Directories already sorted: {processed - sorted_count}")
        
        if sorted_count > 0:
            print("\nFiles have been reordered. The changes should be visible on")
            print("embedded devices that read files in filesystem order.")
        
    except KeyboardInterrupt:
        print("\nOperation interrupted by user.")
        sorter.logger.warning("Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        sorter.logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
