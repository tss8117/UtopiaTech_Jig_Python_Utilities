# ============================================================================
# JIG ONE v1.2 - Core Package
# ============================================================================

from .tlv_parser import (
    TlvParser,
    TlvElement,
    ParsedResults,
    BitmapConfig,
    TlvParseError,
    UnknownTagError,
    InvalidLengthError,
    BitmapValidationError,
    build_tlv,
    build_tlv_uint8,
    build_tlv_uint16_le,
    build_tlv_uint32_le,
    build_tlv_mac,
    get_tlv_parser,
    configure_tlv_parser,
)

from .protocol import (
    RS485Frame,
    ProtocolHandler,
    build_dut_reset_pulse,
    build_led_control,
    build_all_leds_off,
)

from .serial_handler import (
    SerialPortInfo,
    SerialHandler,
    serial_handler,
)

from .retest_manager import (
    RetestAttempt,
    RetestManager,
    category_to_mask,
    mask_to_categories,
    mask_to_string,
)

from .state_machine import (
    StateMachineEvent,
    TestStateMachine,
)

__all__ = [
    # TLV Parser (v1.2)
    'TlvParser',
    'TlvElement',
    'ParsedResults',
    'BitmapConfig',
    'TlvParseError',
    'UnknownTagError',
    'InvalidLengthError',
    'BitmapValidationError',
    'build_tlv',
    'build_tlv_uint8',
    'build_tlv_uint16_le',
    'build_tlv_uint32_le',
    'build_tlv_mac',
    'get_tlv_parser',
    'configure_tlv_parser',
    # Protocol
    'RS485Frame',
    'ProtocolHandler',
    'build_dut_reset_pulse',
    'build_led_control',
    'build_all_leds_off',
    # Serial
    'SerialPortInfo',
    'SerialHandler',
    'serial_handler',
    # Retest
    'RetestAttempt',
    'RetestManager',
    'category_to_mask',
    'mask_to_categories',
    'mask_to_string',
    # State Machine
    'StateMachineEvent',
    'TestStateMachine',
]
