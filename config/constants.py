# ============================================================================
# JIG ONE v1.2 - Protocol Constants
# ============================================================================
# Based on JIG_ONE_PROTOCOL_v1.2.md - TLV Format
# ============================================================================

from enum import Enum, IntEnum, auto

# ============================================================================
# VERSION INFO
# ============================================================================
JIG_FORMAT_VERSION = "JIG-ONE-1.2"
VERSION = "1.2.0"
PROTOCOL_VERSION = "1.2"

# ============================================================================
# FRAME CONSTANTS
# ============================================================================
START_BYTE = 0x7D
END_BYTE = 0xD9
MIN_FRAME_SIZE = 7  # Header(4) + TLV(2 min) + Footer(1)
MAX_DATA_LENGTH = 255

# Frame Position Index
class FrameIndex(IntEnum):
    HEADER = 0
    FROM_ADDR = 1
    TO_ADDR = 2
    DATA_LENGTH = 3
    DATA_START = 4  # TLV payload starts here


# ============================================================================
# DEVICE ADDRESSES
# ============================================================================
class DeviceAddress(IntEnum):
    JIG_BOARD = 0xAA    # JIG Board (Master Controller with integrated CLOCK_M)
    DUT = 0xBB          # Device Under Test
    RASPI = 0xCC        # Raspberry Pi (Supervisor)


# ============================================================================
# TLV TAGS (Protocol v1.2)
# ============================================================================
class TlvTag(IntEnum):
    """
    TLV Tag definitions for Protocol v1.2
    
    Tag Ranges:
    - 0x01 - 0x0F : Test Result Tags
    - 0x10 - 0x1F : Additional/Custom Test Tags (Reserved)
    - 0x80 - 0x8F : Sub-Field Tags (for compound TLVs)
    - 0x90 - 0x9F : Control Tags
    - 0xD0 - 0xDF : Configuration Tags
    - 0xE0 - 0xEF : Programming Tags
    - 0xF0 - 0xF5 : Retest Tags
    - 0xF6 - 0xFB : JIG Control Tags
    - 0xFC - 0xFF : Error/Status Tags
    """
    
    # ══════════════════════════════════════════════════════════════
    # TEST RESULT TAGS (0x01 - 0x0F)
    # ══════════════════════════════════════════════════════════════
    PERIPHERALS = 0x01          # Peripheral bitmap (2 bytes LE)
    DIG_INPUTS = 0x04           # Digital input bitmap (8 bytes LE)
    RELAYS = 0x05               # Relay bitmap (2 bytes LE)
    MEASURE_LSE = 0x06          # Clock frequency Hz (4 bytes LE)
    
    # ══════════════════════════════════════════════════════════════
    # ADDITIONAL TEST TAGS (0x10 - 0x1F) - Reserved for expansion
    # ══════════════════════════════════════════════════════════════
    TEST_CALIBRATION = 0x10     # Calibration test (reserved)
    TEST_AUDIO = 0x11           # Audio test (reserved)
    TEST_DISPLAY = 0x12         # Display test (reserved)
    
    # ══════════════════════════════════════════════════════════════
    # SUB-FIELD TAGS (0x80 - 0x8F) - For compound TLVs
    # ══════════════════════════════════════════════════════════════
    SERIAL_NO = 0x80            # Serial number (4 bytes LE)
    MAC_ID = 0x81               # MAC address (6 bytes LE)
    RTC_TIMESTAMP = 0x82        # Unix timestamp (4 bytes LE)
    RELAY_ID = 0x83             # Relay ID (1 byte)
    RELAY_STATE = 0x84          # Relay state (1 byte)
    FW_TYPE = 0x85              # Firmware type (1 byte)
    RESULT_STATUS = 0x86        # Result status (1 byte)
    ERROR_CODE = 0x87           # Error code (1 byte)
    RETEST_MASK = 0x88          # Retest category mask (4 bytes LE)
    ACK_STATUS = 0x89           # ACK/NACK status (1 byte)
    PROG_STATUS = 0x8A          # Programming status (1 byte)
    
    # ══════════════════════════════════════════════════════════════
    # CONTROL TAGS (0x90 - 0x9F)
    # ══════════════════════════════════════════════════════════════
    START_TEST = 0x99           # Start test sequence
    
    # ══════════════════════════════════════════════════════════════
    # CONFIGURATION TAGS (0xD0 - 0xDF)
    # ══════════════════════════════════════════════════════════════
    SET_CONFIG = 0xDA           # Set configuration marker
    
    # ══════════════════════════════════════════════════════════════
    # PROGRAMMING TAGS (0xE0 - 0xEF)
    # ══════════════════════════════════════════════════════════════
    START_PROG = 0xEA           # Start programming sequence
    PROG_FINAL = 0xEB           # Final firmware programming state
    PROG_ACK = 0xEC             # Programming acknowledgment
    # NOTE: TAG_RESULTS (0xEE) REMOVED in v1.2 - frame end = results complete
    
    # ══════════════════════════════════════════════════════════════
    # RETEST TAGS (0xF0 - 0xF5)
    # ══════════════════════════════════════════════════════════════
    RETEST = 0xF0               # Request retest (uses RETEST_MASK sub-field)
    RETEST_ACK = 0xF1           # Retest acknowledgment
    
    # ══════════════════════════════════════════════════════════════
    # JIG CONTROL TAGS (0xF6 - 0xFB)
    # ══════════════════════════════════════════════════════════════
    JIG_RELAY = 0xFA            # JIG relay control marker
    
    # ══════════════════════════════════════════════════════════════
    # ERROR/STATUS TAGS (0xFC - 0xFF)
    # ══════════════════════════════════════════════════════════════
    COMM_FAILED = 0xF9          # Communication failure
    DISPLAY_FAIL1 = 0xFB        # Display fail indicator 1
    DISPLAY_FAIL2 = 0xFC        # Display fail indicator 2
    DISPLAY_FAIL3 = 0xFD        # Display fail indicator 3


# ============================================================================
# KNOWN TAG SET (for validation)
# ============================================================================
KNOWN_TLV_TAGS = {tag.value for tag in TlvTag}


# ============================================================================
# TLV TAG EXPECTED LENGTHS (for validation)
# ============================================================================
TLV_EXPECTED_LENGTHS = {
    # Test Results - lengths calculated from JSON, but these are protocol maximums
    TlvTag.PERIPHERALS: 2,      # 2 bytes (16 bits max)
    TlvTag.DIG_INPUTS: 8,       # 8 bytes (64 bits max)
    TlvTag.RELAYS: 2,           # 2 bytes (16 bits max)
    TlvTag.MEASURE_LSE: 4,      # 4 bytes (uint32 Hz)
    
    # Sub-field Tags
    TlvTag.SERIAL_NO: 4,        # uint32 LE
    TlvTag.MAC_ID: 6,           # 6 bytes MAC
    TlvTag.RTC_TIMESTAMP: 4,    # uint32 Unix timestamp
    TlvTag.RELAY_ID: 1,         # 1 byte
    TlvTag.RELAY_STATE: 1,      # 1 byte
    TlvTag.FW_TYPE: 1,          # 1 byte
    TlvTag.RESULT_STATUS: 1,    # 1 byte
    TlvTag.ERROR_CODE: 1,       # 1 byte
    TlvTag.RETEST_MASK: 4,      # uint32 LE
    TlvTag.ACK_STATUS: 1,       # 1 byte
    TlvTag.PROG_STATUS: 1,      # 1 byte
    
    # Control Tags
    TlvTag.START_TEST: 0,       # No payload (marker only)
    TlvTag.START_PROG: 1,       # 1 byte status
}


# ============================================================================
# COMBINED RESULTS FRAME SIZE
# ============================================================================
# TLV1: PERI (2+2=4) + TLV2: CLOCK (2+4=6) + TLV3: DIG (2+8=10) + TLV4: RELAY (2+2=4)
COMBINED_RESULTS_DATA_LENGTH = 24  # 0x18
COMBINED_RESULTS_FRAME_SIZE = 29   # Header(4) + Data(24) + Footer(1)


# ============================================================================
# JIG RELAY IDs (Protocol v1.2)
# ============================================================================
class JigRelayID(IntEnum):
    RED_LED = 0x01      # Fail indicator LED
    GREEN_LED = 0x02    # Pass indicator LED
    RESET = 0x03        # DUT reset control
    SPARE_1 = 0x04      # Spare relay 1
    SPARE_2 = 0x05      # Spare relay 2


class RelayState(IntEnum):
    OFF = 0x00
    ON = 0x01


# ============================================================================
# FIRMWARE TYPES
# ============================================================================
class FirmwareType(IntEnum):
    BOOTLOADER = 0x01
    TEST_CODE = 0x02
    FINAL = 0x03


# ============================================================================
# RETEST MASKS (Protocol v1.2 - uint32_t, 4 bytes Little Endian)
# ============================================================================
class RetestMask:
    """Retest category masks - uint32_t (4 bytes)"""
    NONE = 0x00000000
    PERIPHERALS = 0x00000001    # Bit 0
    DIG_INPUTS = 0x00000002     # Bit 1
    RELAYS = 0x00000004         # Bit 2
    ADDITIONAL = 0x00000008     # Bit 3 (reserved for future)
    ALL = 0xFFFFFFFF


# ============================================================================
# PROGRAMMING STATUS
# ============================================================================
class ProgStatus(IntEnum):
    IDLE = 0x00
    SUCCESS = 0x01
    FAILED = 0x02
    NO_SCAN = 0x03
    NO_FILES = 0x04
    TIMEOUT = 0x05
    RETRY = 0x06


# ============================================================================
# TEST STATUS
# ============================================================================
class TestStatus(IntEnum):
    IDLE = 0x00
    STARTED = 0x01
    COMPLETE = 0x02
    PASS = 0x03
    FAIL = 0x04
    RETESTING = 0x05


# ============================================================================
# ERROR CODES
# ============================================================================
class ErrorCode(IntEnum):
    NONE = 0x00
    COMM_GENERAL = 0x01
    TIMEOUT = 0x02
    INVALID_FRAME = 0x03
    CONFIG_VERIFY = 0x04
    PROG_FAILED = 0x05
    UNKNOWN_CMD = 0x06


# ============================================================================
# STATE MACHINE STATES (Protocol v1.2 - Clean Hex Groups)
# ============================================================================
class JigState(IntEnum):
    # Programming States (0x00 - 0x0F)
    PROG_IDLE = 0x00
    PROG_BOOT = 0x01
    PROG_TEST = 0x02
    PROG_FINAL = 0x03
    
    # Test States (0x10 - 0x1F)
    TEST_PERI = 0x10
    TEST_ZONE = 0x11
    TEST_RELAY = 0x12
    TEST_CLOCK = 0x13
    TEST_ADDITIONAL = 0x14
    
    # Result & Config States (0x20 - 0x2F)
    SEND_RESULT = 0x20
    WAIT_CONFIG = 0x21
    RETEST = 0x22
    
    # Idle States (0xF0 - 0xFF)
    PRE_IDLE = 0xFE
    IDLE = 0xFF


# ============================================================================
# APPLICATION STATE (for RASPi utility)
# ============================================================================
class AppState(Enum):
    # Bootloader States
    BOOTLOADER_NULL = auto()
    BOOTLOADER_PROGRAMMED_PASS = auto()
    BOOTLOADER_PROGRAMMED_FAIL = auto()
    BOOTLOADER_PROGRAMMED_DUT_RST = auto()
    
    # Test Firmware States
    TEST_FIRM_NULL = auto()
    TEST_FIRM_PROGRAMMED_PASS = auto()
    TEST_FIRM_PROGRAMMED_FAIL = auto()
    
    # Testing Process States
    TESTING_PROCESS_NULL = auto()
    TESTING_PROCESS_PASS = auto()
    TESTING_PROCESS_FAIL = auto()
    
    # Setting Configuration States
    SETTING_CONF_NULL = auto()
    SETTING_CONF_PASS = auto()
    SETTING_CONF_FAIL = auto()
    
    # Final Firmware States
    FINAL_FIRM_NULL = auto()
    FINAL_FIRM_PROGRAMMED_PASS = auto()
    FINAL_FIRM_PROGRAMMED_FAIL = auto()
    
    # Auto Mode States
    AUTO_PROGRAM_NULL = auto()
    AUTO_PROGRAM_START = auto()
    AUTO_PROGRAM_BOOTLOADER = auto()
    AUTO_PROGRAM_TEST_FIRM = auto()
    AUTO_TESTING_PROCESS = auto()
    AUTO_TESTING_COMPLETE = auto()
    AUTO_SETTING_CONF_PROCESS = auto()
    AUTO_SETTING_CONF_COMPLETE = auto()
    AUTO_PROGRAM_FINAL_FIRM = auto()
    AUTO_NO_COMMUNICATION = auto()
    AUTO_RETESTING = auto()


# ============================================================================
# TEST MODE & RETEST STRATEGY
# ============================================================================
class TestMode(Enum):
    USER_MODE = auto()
    DEVELOPER_MODE = auto()


class RetestStrategy(Enum):
    FULL_SEQUENCE = auto()
    FAILED_ONLY = auto()
    SPECIFIC_TEST = auto()


class TestCategory(Enum):
    PERIPHERALS = auto()
    DIGITAL_INPUTS = auto()
    RELAYS = auto()
    ADDITIONAL = auto()  # Placeholder for future tests
    ALL = auto()


# ============================================================================
# LEGACY COMMAND IDs (Deprecated in v1.2 - kept for reference)
# ============================================================================
class CommandID(IntEnum):
    """
    DEPRECATED: v1.1 Command IDs
    In v1.2, use TlvTag instead. These are kept for backward reference only.
    """
    # Test Result Commands (0x01 - 0x0F) -> Now TLV Tags
    PERIPHERALS = 0x01
    DIG_INPUTS = 0x04
    RELAYS = 0x05
    MEASURE_LSE = 0x06
    
    # Control Commands (0x90 - 0x9F)
    START_TEST = 0x99
    
    # Configuration Commands (0xD0 - 0xDF)
    SET_CONFIG = 0xDA
    
    # Programming Commands (0xE0 - 0xEF)
    START_PROG = 0xEA
    PROG_FINAL = 0xEB
    PROG_ACK = 0xEC
    # RESULTS = 0xEE  # REMOVED in v1.2
    
    # Retest Commands (0xF0 - 0xF5)
    RETEST = 0xF0
    RETEST_ACK = 0xF1
    
    # JIG Control Commands (0xF6 - 0xFB)
    JIG_RELAY = 0xFA
    
    # Error/Status Commands (0xFC - 0xFF)
    COMM_FAILED = 0xF9
