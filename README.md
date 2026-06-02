# JIG ONE v1.2 - Testing Utility

A modular RS485-based testing system for electronic boards with integrated CLOCK_M functionality and TLV protocol format.

## 🆕 What's New in v1.2

### Protocol Changes
- **TLV Format**: All DATA fields now use Type-Length-Value structure
- **Combined Results Frame**: All test results in single 29-byte frame
- **Self-Describing**: Each field carries its own length for robust parsing
- **No TAG_RESULTS**: Frame end (0xD9) signals results complete

### Logging Improvements
- **Monthly + Daily Excel**: Dual logging to monthly rollup and daily files
- **S3 Upload Workflow**: Pending_Upload/S3_Uploaded folder structure for cron-based sync
- **Clock Frequency Column**: Raw Hz value logged in Excel
- **Attempt Tracking**: Each test attempt logged as separate row

## 📁 Project Structure

```
jig_one_v1.2/
├── main.py                     # Entry point
├── README.md                   # This file
│
├── config/                     # Configuration
│   ├── __init__.py
│   ├── constants.py            # Protocol constants (v1.2 TLV tags)
│   ├── settings.py             # Application settings
│   └── products/               # Product JSON configs
│       ├── ess_main_board.json # Default product
│       └── fire_alarm_panel.json
│
├── core/                       # Core functionality
│   ├── __init__.py
│   ├── tlv_parser.py           # NEW: Dynamic TLV parser
│   ├── protocol.py             # RS485 frame building/parsing (TLV)
│   ├── serial_handler.py       # Serial communication
│   ├── retest_manager.py       # Retry logic (uint32_t masks)
│   └── state_machine.py        # Test sequence controller
│
├── models/                     # Data models
│   ├── __init__.py
│   ├── product_config.py       # JSON config loader
│   └── test_results.py         # Test result & attempt tracking
│
├── gui/                        # User interface
│   ├── __init__.py
│   ├── main_window.py          # Main window (combined results handling)
│   ├── frames/                 # GUI frames
│   │   ├── serial_frame.py
│   │   ├── config_frame.py
│   │   ├── results_frame.py
│   │   └── developer_frame.py
│   └── widgets/
│       ├── status_button.py
│       └── log_textbox.py
│
├── services/                   # External services
│   ├── __init__.py
│   ├── excel_logger.py         # Monthly/Daily Excel logging
│   ├── programmer.py           # OpenOCD firmware programming
│   └── qr_scanner.py           # Barcode/QR scanning
│
├── utils/                      # Utilities
│   ├── __init__.py
│   ├── text_logger.py          # Per-DUT text logs
│   ├── file_helpers.py
│   └── thread_helpers.py
│
├── Config_Template/            # OpenOCD templates
│   ├── boot_template_openocd.cfg
│   └── template_openocd.cfg
│
├── Offline_Logs/               # Excel logs (created at runtime)
│   ├── YYYY-MM/
│   │   ├── PRODUCT_YYYY-MM_monthly.xlsx
│   │   └── YYYY-MM-DD/
│   │       └── PRODUCT_YYYY-MM-DD.xlsx
│   ├── Pending_Upload/
│   │   ├── monthly/
│   │   └── daily/
│   └── S3_Uploaded/
│       ├── monthly/
│       └── daily/
│
└── Test_Logs/                  # Per-DUT text logs
```

## 🚀 Usage

### Basic Usage
```bash
# User Mode (default)
python3 main.py

# Developer Mode
python3 main.py --dev
python3 main.py -d
```

### Multi-Product Support
```bash
# Default product (ess_main_board.json)
python3 main.py

# Select different product
python3 main.py --product fire_alarm_panel
python3 main.py -p custom_board

# Combined with dev mode
python3 main.py --dev -p fire_alarm_panel
```

### Help & Version
```bash
python3 main.py --help
python3 main.py --version
```

## 📋 Requirements

```bash
pip install customtkinter pyserial openpyxl
```

## ⚙️ Key Features

### 1. TLV Protocol Format (v1.2)

All DATA fields use Type-Length-Value structure:
```
┌─────────────┬─────────────┬─────────────────────────┐
│    TAG      │   LENGTH    │         VALUE           │
│   (1 byte)  │  (1 byte)   │      (L bytes)          │
└─────────────┴─────────────┴─────────────────────────┘
```

### 2. Combined Results Frame

All test results sent in a single 29-byte frame:
```
Frame: 0x7D | 0xAA | 0xCC | 0x18 | [TLV Data 24 bytes] | 0xD9

TLV Data breakdown:
- Peripherals:    TAG=0x01, LEN=0x02, VALUE=2 bytes (bitmap)
- Clock Freq:     TAG=0x06, LEN=0x04, VALUE=4 bytes (Hz, LE)
- Digital Inputs: TAG=0x04, LEN=0x08, VALUE=8 bytes (bitmap)
- Relays:         TAG=0x05, LEN=0x02, VALUE=2 bytes (bitmap)
```

### 3. Dynamic Configuration from JSON

The GUI and TLV parser automatically adapt to product JSON:
```json
{
    "product_name": "ESS Main Board",
    "peripherals": [...],       // Dynamic bitmap size
    "digital_inputs": {...},    // Zones + additional
    "relays": {...}             // Dynamic count
}
```

### 4. Excel Logging Structure

**Monthly File** (accumulates all month's tests):
```
Offline_Logs/2025-12/ESS_MAIN_2025-12_monthly.xlsx
```

**Daily Files** (one per day):
```
Offline_Logs/2025-12/2025-12-25/ESS_MAIN_2025-12-25.xlsx
```

**Upload Workflow**:
- On boot, previous day's daily file moves to `Pending_Upload/daily/`
- On 1st of month, previous month's folder moves to `Pending_Upload/monthly/`
- External cron script uploads and moves to `S3_Uploaded/`

### 5. Excel Columns

| Column | Description |
|--------|-------------|
| Date | Test date (DD-MM-YYYY) |
| Time | Test time (HH:MM:SS) |
| Serial No. | Device serial number |
| MAC ID | Device MAC address |
| Config State | SET or NOT SET |
| Attempt | Test attempt number (1, 2, 3...) |
| Clock Frequency Hz | Raw clock frequency in Hz |
| [Peripherals] | PASS/FAIL for each peripheral |
| [Zones] | PASS/FAIL for each zone |
| [Relays] | PASS/FAIL for each relay |

### 6. Test Modes

| Mode | Retries | Strategy | Controls |
|------|---------|----------|----------|
| User | 2 (auto) | FAILED_ONLY | Hidden |
| Developer | Up to 10 | Configurable | Visible |

## 🔧 Protocol v1.2 Quick Reference

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    JIG ONE v1.2 QUICK REFERENCE (TLV)                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ FRAME FORMAT                                                                 ║
║   0x7D | FROM | TO | LEN | [TLV1] [TLV2] ... | 0xD9                          ║
║   Each TLV: | TAG (1B) | LEN (1B) | VALUE (LEN bytes) |                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ DEVICE ADDRESSES                                                             ║
║   JIG Board = 0xAA    DUT = 0xBB    RASPi = 0xCC                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ TEST RESULT TAGS (Combined in single frame)                                  ║
║   0x01 PERIPHERALS (L=2)   0x04 DIG_INPUTS (L=8)   0x05 RELAYS (L=2)        ║
║   0x06 MEASURE_LSE (L=4)                                                     ║
║   NOTE: All sent in ONE frame (29 bytes) - no TAG_RESULTS needed!           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ SUB-FIELD TAGS (0x80 - 0x8F)                                                 ║
║   0x80 SERIAL_NO (L=4)     0x81 MAC_ID (L=6)       0x82 RTC_TS (L=4)        ║
║   0x83 RELAY_ID (L=1)      0x84 RELAY_STATE (L=1)  0x85 FW_TYPE (L=1)       ║
║   0x86 RESULT_ST (L=1)     0x87 ERR_CODE (L=1)     0x88 RETEST_MASK (L=4)   ║
║   0x89 ACK_STATUS (L=1)    0x8A PROG_STATUS (L=1)                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ RETEST MASK VALUES (uint32_t LE)                                             ║
║   PERI = 0x00000001   DIG = 0x00000002   RELAY = 0x00000004                 ║
║   ADDITIONAL = 0x00000008   ALL = 0xFFFFFFFF                                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ JIG RELAYS (ID values for TAG_RELAY_ID)                                      ║
║   RED_LED = 0x01   GREEN_LED = 0x02   RESET = 0x03                          ║
║   State (TAG_RELAY_STATE): OFF = 0x00   ON = 0x01                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

## 📝 Creating a New Product Config

1. Copy `config/products/ess_main_board.json`
2. Rename to `your_product.json`
3. Edit the JSON to match your product's test requirements
4. Run with: `python3 main.py -p your_product`

### JSON Structure
```json
{
    "product_name": "Product Display Name",
    "product_code": "PRODUCT_CODE",
    "version": "1.0",
    
    "peripherals": [
        {"name": "Test Name", "bit_position": 0, "enabled": true}
    ],
    
    "digital_inputs": {
        "zones": {"count": 36, "name_format": "Zone {n}"},
        "additional": [
            {"name": "Input Name", "index": 36, "enabled": true}
        ]
    },
    
    "relays": {"count": 12, "name_format": "Relay {n}"},
    
    "clock": {
        "nominal_hz": 32768,
        "min_hz": 32000,
        "max_hz": 32900
    },
    
    "firmware": {
        "bootloader": {"path": "", "openocd_template": "..."},
        "test_code": {"path": "", "openocd_template": "..."},
        "final_firmware": {"path": "", "openocd_template": "..."}
    },
    
    "additional_tests": []
}
```

## 🔄 S3 Upload Cron Script (Example)

Create a cron job to run this script periodically:

```bash
#!/bin/bash
# /home/pi/s3_upload.sh

PENDING_MONTHLY="/path/to/Offline_Logs/Pending_Upload/monthly"
PENDING_DAILY="/path/to/Offline_Logs/Pending_Upload/daily"
UPLOADED_MONTHLY="/path/to/Offline_Logs/S3_Uploaded/monthly"
UPLOADED_DAILY="/path/to/Offline_Logs/S3_Uploaded/daily"
S3_BUCKET="s3://your-bucket/jig-logs"

# Upload monthly files
for file in "$PENDING_MONTHLY"/*; do
    if [ -f "$file" ]; then
        aws s3 cp "$file" "$S3_BUCKET/monthly/" && mv "$file" "$UPLOADED_MONTHLY/"
    fi
done

# Upload daily files
for file in "$PENDING_DAILY"/*; do
    if [ -f "$file" ]; then
        aws s3 cp "$file" "$S3_BUCKET/daily/" && mv "$file" "$UPLOADED_DAILY/"
    fi
done
```

Add to crontab:
```
# Run every hour
0 * * * * /home/pi/s3_upload.sh
```

## 🔧 Migration from v1.1

### Breaking Changes
1. **Frame format**: All commands now use TLV structure
2. **Combined results**: No separate TAG_RESULTS (0xEE) marker
3. **Excel structure**: Monthly files with daily subfolders
4. **Column changes**: "Serial State" → "Config State", added "Attempt" and "Clock Frequency Hz"

### Firmware Updates Required
- JIG Board firmware must send combined results frame
- All responses must use TLV format
- Frame end (0xD9) indicates results complete

---

**Version**: 1.2.0  
**Protocol**: v1.2 (TLV)  
**Date**: December 2025
