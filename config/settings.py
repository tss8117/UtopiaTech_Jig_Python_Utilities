# ============================================================================
# JIG ONE v1.2 - Application Settings
# ============================================================================

import os
import sys

# ============================================================================
# BASE DIRECTORIES
# ============================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
PRODUCTS_DIR = os.path.join(CONFIG_DIR, 'products')
OFFLINE_LOGS_DIR = os.path.join(BASE_DIR, 'Offline_Logs')
TEST_LOGS_DIR = os.path.join(BASE_DIR, 'Test_Logs')
CONFIG_TEMPLATE_DIR = os.path.join(BASE_DIR, 'Config_Template')
FIRMWARE_DIR = os.path.join(BASE_DIR, 'Firmware')

# Ensure directories exist
for dir_path in [CONFIG_DIR, PRODUCTS_DIR, OFFLINE_LOGS_DIR, TEST_LOGS_DIR, CONFIG_TEMPLATE_DIR, FIRMWARE_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ============================================================================
# OPENOCD TEMPLATES
# ============================================================================
BOOTLOADER_OPENOCD_TEMPLATE = os.path.join(CONFIG_TEMPLATE_DIR, 'boot_template_openocd.cfg')
FIRMWARE_OPENOCD_TEMPLATE = os.path.join(CONFIG_TEMPLATE_DIR, 'template_openocd.cfg')

# ============================================================================
# SERIAL SETTINGS
# ============================================================================
SERIAL_BAUDRATE = 9600
SERIAL_TIMEOUT = 1.0  # seconds

# ============================================================================
# TIMING SETTINGS (in seconds)
# ============================================================================
PROGRAMMING_TIMEOUT = 20  # OpenOCD programming timeout
RESPONSE_TIMEOUT = 10     # Max wait for response
INTER_FRAME_DELAY = 0.3   # Delay between frames
RETEST_DELAY = 0.3        # Delay before retest
DUT_RESET_PULSE = 2.0     # Reset pulse duration
CONFIG_RETRY_DELAY = 0.5  # Delay between config attempts

# ============================================================================
# RETRY SETTINGS
# ============================================================================
# User Mode
USER_MODE_MAX_RETRIES = 1  # 1 main test + 1 automatic retry

# Developer Mode
MAX_DEVELOPER_RETRIES = 10
DEFAULT_DEVELOPER_RETRIES = 3

# ============================================================================
# DEVELOPER MODE DEFAULTS
# ============================================================================
DEV_DEFAULT_SERIAL_NO = "32999999"
DEV_DEFAULT_MAC_ID = "AABBCCDDEEFF"

# ============================================================================
# DEVELOPER MODE FLAG
# ============================================================================
def parse_developer_mode() -> bool:
    """Parse command line arguments for developer mode"""
    dev_flags = ['--dev', '--developer', '-d', '--debug']
    for arg in sys.argv[1:]:
        if arg.lower() in dev_flags:
            return True
    return False

DEVELOPER_MODE_ENABLED = parse_developer_mode()

# ============================================================================
# PRODUCT SELECTION
# ============================================================================
# Default product config file
DEFAULT_PRODUCT_CONFIG = "ess_main_board.json"

def parse_product_config() -> str:
    """Parse command line for product config selection
    
    Usage: python main.py --product <config_name>
           python main.py -p ess_main_board
    """
    product_flags = ['--product', '-p']
    args = sys.argv[1:]
    
    for i, arg in enumerate(args):
        if arg.lower() in product_flags and i + 1 < len(args):
            config_name = args[i + 1]
            # Add .json extension if not present
            if not config_name.endswith('.json'):
                config_name += '.json'
            return config_name
    
    return DEFAULT_PRODUCT_CONFIG

SELECTED_PRODUCT_CONFIG = parse_product_config()

def get_product_config_path() -> str:
    """Get full path to selected product config"""
    return os.path.join(PRODUCTS_DIR, SELECTED_PRODUCT_CONFIG)

# ============================================================================
# GUI SETTINGS
# ============================================================================
# Default screen dimensions (will be overridden dynamically)
DEFAULT_SCREEN_WIDTH = 1920
DEFAULT_SCREEN_HEIGHT = 1080

# Screen coverage ratio (90% of screen by default)
SCREEN_COVERAGE_RATIO = 1.0

# Minimum window dimensions
MIN_WINDOW_WIDTH = 1280
MIN_WINDOW_HEIGHT = 720

DEFAULT_COLOR = "#313bc2"
PASS_COLOR = "#8dff50"
FAIL_COLOR = "red"
PENDING_COLOR = "yellow"
DEFAULT_GRAY = "grey"

def get_screen_dimensions(root=None) -> tuple:
    """
    Get actual screen dimensions.
    
    Args:
        root: Tk root window (if available)
        
    Returns:
        Tuple of (width, height)
    """
    if root:
        try:
            return root.winfo_screenwidth(), root.winfo_screenheight()
        except:
            pass
    return DEFAULT_SCREEN_WIDTH, DEFAULT_SCREEN_HEIGHT

def get_window_dimensions(root=None, coverage: float = None) -> tuple:
    """
    Get window dimensions based on screen size and coverage ratio.
    
    Args:
        root: Tk root window
        coverage: Screen coverage ratio (0.0-1.0), defaults to SCREEN_COVERAGE_RATIO
        
    Returns:
        Tuple of (width, height, x_offset, y_offset)
    """
    if coverage is None:
        coverage = SCREEN_COVERAGE_RATIO
    
    screen_w, screen_h = get_screen_dimensions(root)
    
    # Calculate window size
    win_w = max(int(screen_w * coverage), MIN_WINDOW_WIDTH)
    win_h = max(int(screen_h * coverage), MIN_WINDOW_HEIGHT)
    
    # Center the window
    x_offset = (screen_w - win_w) // 2
    y_offset = (screen_h - win_h) // 2
    
    return win_w, win_h, x_offset, y_offset

# ============================================================================
# LOG SETTINGS
# ============================================================================
LOG_DATE_FORMAT = "%Y-%m-%d"
LOG_TIME_FORMAT = "%H:%M:%S"
LOG_DATETIME_FORMAT = "%d-%m-%Y %H:%M:%S"
LOG_FILENAME_FORMAT = "%Y-%m-%d_%H-%M-%S"

# ============================================================================
# PRINT STARTUP INFO
# ============================================================================
if DEVELOPER_MODE_ENABLED:
    print("=" * 50)
    print("  DEVELOPER MODE ACTIVATED")
    print(f"  Product Config: {SELECTED_PRODUCT_CONFIG}")
    print(f"  Protocol: v1.2 (TLV Format)")
    print("=" * 50)
else:
    print(f"[CONFIG] Product: {SELECTED_PRODUCT_CONFIG}")
    print(f"[CONFIG] Protocol: v1.2 (TLV Format)")
