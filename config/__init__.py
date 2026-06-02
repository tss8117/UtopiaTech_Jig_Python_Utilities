# ============================================================================
# JIG ONE v1.2 - Config Package
# ============================================================================

from .constants import (
    JIG_FORMAT_VERSION,
    VERSION,
    PROTOCOL_VERSION,
    START_BYTE,
    END_BYTE,
    FrameIndex,
    DeviceAddress,
    TlvTag,
    KNOWN_TLV_TAGS,
    TLV_EXPECTED_LENGTHS,
    COMBINED_RESULTS_DATA_LENGTH,
    COMBINED_RESULTS_FRAME_SIZE,
    JigRelayID,
    RelayState,
    FirmwareType,
    RetestMask,
    ProgStatus,
    TestStatus,
    ErrorCode,
    JigState,
    AppState,
    TestMode,
    RetestStrategy,
    TestCategory,
    CommandID,  # Legacy, kept for reference
)

from .settings import (
    BASE_DIR,
    CONFIG_DIR,
    PRODUCTS_DIR,
    OFFLINE_LOGS_DIR,
    TEST_LOGS_DIR,
    CONFIG_TEMPLATE_DIR,
    FIRMWARE_DIR,
    BOOTLOADER_OPENOCD_TEMPLATE,
    FIRMWARE_OPENOCD_TEMPLATE,
    SERIAL_BAUDRATE,
    PROGRAMMING_TIMEOUT,
    RESPONSE_TIMEOUT,
    INTER_FRAME_DELAY,
    USER_MODE_MAX_RETRIES,
    MAX_DEVELOPER_RETRIES,
    DEFAULT_DEVELOPER_RETRIES,
    DEV_DEFAULT_SERIAL_NO,
    DEV_DEFAULT_MAC_ID,
    DEVELOPER_MODE_ENABLED,
    SELECTED_PRODUCT_CONFIG,
    get_product_config_path,
    get_screen_dimensions,
    get_window_dimensions,
    MIN_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
    SCREEN_COVERAGE_RATIO,
    DEFAULT_COLOR,
    PASS_COLOR,
    FAIL_COLOR,
    PENDING_COLOR,
    DEFAULT_GRAY,
)

__all__ = [
    # Version
    'JIG_FORMAT_VERSION',
    'VERSION',
    'PROTOCOL_VERSION',
    # Frame
    'START_BYTE',
    'END_BYTE',
    'FrameIndex',
    'DeviceAddress',
    # TLV (v1.2)
    'TlvTag',
    'KNOWN_TLV_TAGS',
    'TLV_EXPECTED_LENGTHS',
    'COMBINED_RESULTS_DATA_LENGTH',
    'COMBINED_RESULTS_FRAME_SIZE',
    # Relays
    'JigRelayID',
    'RelayState',
    'FirmwareType',
    'RetestMask',
    # Status
    'ProgStatus',
    'TestStatus',
    'ErrorCode',
    # States
    'JigState',
    'AppState',
    'TestMode',
    'RetestStrategy',
    'TestCategory',
    # Legacy
    'CommandID',
    # Settings
    'BASE_DIR',
    'DEVELOPER_MODE_ENABLED',
    'SELECTED_PRODUCT_CONFIG',
    'get_product_config_path',
    'USER_MODE_MAX_RETRIES',
    'DEV_DEFAULT_SERIAL_NO',
    'DEV_DEFAULT_MAC_ID',
]
