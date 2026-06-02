#!/usr/bin/env python3
# ============================================================================
# JIG ONE v1.2 - Main Entry Point
# ============================================================================
# ESS Main Board Testing Utility
# 
# USAGE:
#   Normal User Mode:    python3 main.py
#   Developer Mode:      python3 main.py --dev
#                        python3 main.py --developer
#                        python3 main.py -d
#   
#   Product Selection:   python3 main.py --product ess_main_board
#                        python3 main.py -p other_product.json
#
# FEATURES:
#   - Protocol v1.2 with TLV (Type-Length-Value) format
#   - CLOCK_M integration into JIG Board
#   - Dynamic GUI from JSON configuration
#   - Combined results frame (29 bytes)
#   - Monthly/Daily Excel logging with S3 upload workflow
#   - User Mode: Auto 2 retries, FAILED_ONLY strategy
#   - Developer Mode: Up to 10 retries, manual controls
#
# CHANGES FROM v1.1:
#   - TLV format for all DATA fields
#   - Combined results frame (no separate TAG_RESULTS marker)
#   - Monthly Excel files with daily subfolder structure
#   - Pending_Upload/S3_Uploaded workflow for cron-based sync
#   - Clock Frequency Hz column in Excel logs
#   - Attempt tracking per test row
#
# ============================================================================

import sys
import os

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def print_version():
    """Print version information"""
    from config.constants import VERSION, PROTOCOL_VERSION, JIG_FORMAT_VERSION
    print(f"""
JIG ONE Testing Utility
=======================
Version     : {VERSION}
Protocol    : v{PROTOCOL_VERSION}
Format      : {JIG_FORMAT_VERSION}
""")


def print_usage():
    """Print usage information"""
    print("""
JIG ONE v1.2 - Testing Utility

Usage:
  python3 main.py [options]

Options:
  --dev, -d, --developer    Enable developer mode
  --product, -p <name>      Select product config (default: ess_main_board.json)
  --version, -v             Show version information
  --help, -h                Show this help message

Examples:
  python3 main.py                           # User mode, default product
  python3 main.py --dev                     # Developer mode
  python3 main.py -p custom_board           # Load custom_board.json config
  python3 main.py --dev -p test_product     # Dev mode with custom product

Product Configuration:
  Product configs are JSON files in config/products/
  Use the filename without .json extension for -p flag

Protocol v1.2 Features:
  - TLV (Type-Length-Value) format for all data fields
  - Combined test results in single 29-byte frame
  - Self-describing frames for forward compatibility
  - Enhanced error handling with specific error codes

Logging:
  - Monthly Excel files: Offline_Logs/YYYY-MM/PRODUCT_YYYY-MM_monthly.xlsx
  - Daily Excel files:   Offline_Logs/YYYY-MM/YYYY-MM-DD/PRODUCT_YYYY-MM-DD.xlsx
  - Text logs (per-DUT): Test_Logs/SERIAL_TIMESTAMP.txt
  - Pending uploads:     Offline_Logs/Pending_Upload/{monthly,daily}/
  - Completed uploads:   Offline_Logs/S3_Uploaded/{monthly,daily}/
""")


def check_dependencies():
    """Check if required dependencies are installed"""
    missing = []
    
    try:
        import customtkinter
    except ImportError:
        missing.append("customtkinter")
    
    try:
        import serial
    except ImportError:
        missing.append("pyserial")
    
    try:
        import openpyxl
    except ImportError:
        missing.append("openpyxl")
    
    if missing:
        print(f"[ERROR] Missing required dependencies: {', '.join(missing)}")
        print(f"\nInstall with: pip install {' '.join(missing)}")
        return False
    
    return True


def main():
    """Main entry point"""
    # Check for help flag
    if '--help' in sys.argv or '-h' in sys.argv:
        print_usage()
        return
    
    # Check for version flag
    if '--version' in sys.argv or '-v' in sys.argv:
        print_version()
        return
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    try:
        # Import after dependency check
        from gui import MainWindow
        from config.constants import VERSION, PROTOCOL_VERSION
        from config.settings import DEVELOPER_MODE_ENABLED, SELECTED_PRODUCT_CONFIG
        
        print("=" * 60)
        print(f"  JIG ONE Testing Utility v{VERSION}")
        print(f"  Protocol: v{PROTOCOL_VERSION} (TLV Format)")
        print(f"  Product: {SELECTED_PRODUCT_CONFIG}")
        print(f"  Mode: {'DEVELOPER' if DEVELOPER_MODE_ENABLED else 'USER'}")
        print("=" * 60)
        
        # Create and run the main window
        app = MainWindow()
        app.run()
        
    except KeyboardInterrupt:
        print("\n[JIG ONE] Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[JIG ONE] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
