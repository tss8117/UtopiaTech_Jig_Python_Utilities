# ============================================================================
# JIG ONE v1.2 - TLV Parser Module
# ============================================================================
# Dynamic TLV parsing based on product JSON configuration
# ============================================================================

import struct
import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from config.constants import (
    TlvTag,
    KNOWN_TLV_TAGS,
    TLV_EXPECTED_LENGTHS,
    COMBINED_RESULTS_DATA_LENGTH,
)


# ============================================================================
# EXCEPTIONS
# ============================================================================

class TlvParseError(Exception):
    """Base exception for TLV parsing errors"""
    pass


class UnknownTagError(TlvParseError):
    """Raised when an unknown TLV tag is encountered"""
    def __init__(self, tag: int):
        self.tag = tag
        super().__init__(f"Unknown TLV tag: 0x{tag:02X}")


class InvalidLengthError(TlvParseError):
    """Raised when TLV length doesn't match expected"""
    def __init__(self, tag: int, expected: int, actual: int):
        self.tag = tag
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Invalid length for tag 0x{tag:02X}: expected {expected}, got {actual}"
        )


class BitmapValidationError(TlvParseError):
    """Raised when bitmap has unexpected bits set"""
    def __init__(self, category: str, expected_bits: int, actual_value: int):
        self.category = category
        self.expected_bits = expected_bits
        self.actual_value = actual_value
        extra_bits = actual_value & ~((1 << expected_bits) - 1)
        super().__init__(
            f"Bitmap validation failed for {category}: "
            f"expected {expected_bits} bits, but value 0x{actual_value:X} has extra bits set (0x{extra_bits:X})"
        )


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class TlvElement:
    """Single parsed TLV element"""
    tag: int
    length: int
    value: bytes
    
    @property
    def tag_name(self) -> str:
        """Get human-readable tag name"""
        try:
            return TlvTag(self.tag).name
        except ValueError:
            return f"UNKNOWN_0x{self.tag:02X}"
    
    def value_as_int(self, byteorder: str = 'little') -> int:
        """Convert value bytes to integer"""
        return int.from_bytes(self.value, byteorder)
    
    def __repr__(self):
        hex_value = self.value.hex().upper()
        return f"TLV({self.tag_name}, len={self.length}, value=0x{hex_value})"


@dataclass
class ParsedResults:
    """Parsed combined test results"""
    peripheral_bitmap: int = 0
    peripheral_byte_count: int = 0
    clock_frequency_hz: int = 0
    digital_input_bitmap: int = 0
    digital_input_byte_count: int = 0
    relay_bitmap: int = 0
    relay_byte_count: int = 0
    raw_tlvs: List[TlvElement] = field(default_factory=list)
    
    # Interpreted results (populated after validation)
    peripheral_results: Dict[str, bool] = field(default_factory=dict)
    digital_input_results: Dict[str, bool] = field(default_factory=dict)
    relay_results: Dict[str, bool] = field(default_factory=dict)
    clock_pass: bool = False


@dataclass
class BitmapConfig:
    """Configuration for bitmap parsing from JSON"""
    peripheral_count: int = 0
    peripheral_names: List[str] = field(default_factory=list)
    digital_input_count: int = 0
    digital_input_names: List[str] = field(default_factory=list)
    relay_count: int = 0
    relay_names: List[str] = field(default_factory=list)
    clock_min_hz: int = 32000
    clock_max_hz: int = 32900
    clock_nominal_hz: int = 32768
    
    @property
    def peripheral_bytes(self) -> int:
        """Calculate bytes needed for peripheral bitmap"""
        return max(1, math.ceil(self.peripheral_count / 8))
    
    @property
    def digital_input_bytes(self) -> int:
        """Calculate bytes needed for digital input bitmap"""
        return max(1, math.ceil(self.digital_input_count / 8))
    
    @property
    def relay_bytes(self) -> int:
        """Calculate bytes needed for relay bitmap"""
        return max(1, math.ceil(self.relay_count / 8))


# ============================================================================
# TLV PARSER CLASS
# ============================================================================

class TlvParser:
    """
    Dynamic TLV parser that adapts to product configuration.
    
    Features:
    - Parses TLV frames according to Protocol v1.2
    - Dynamically calculates expected bitmap sizes from JSON config
    - Validates tags and lengths
    - Raises errors on unknown tags or validation failures
    """
    
    def __init__(self, bitmap_config: Optional[BitmapConfig] = None):
        """
        Initialize TLV parser.
        
        Args:
            bitmap_config: Configuration loaded from product JSON.
                          If None, uses protocol maximum sizes.
        """
        self.config = bitmap_config or BitmapConfig()
        self._strict_validation = True
    
    @classmethod
    def from_product_config(cls, product_config) -> 'TlvParser':
        """
        Create TlvParser from ProductConfig instance.
        
        Args:
            product_config: ProductConfig instance loaded from JSON
            
        Returns:
            Configured TlvParser instance
        """
        config = BitmapConfig()
        
        # Peripherals
        config.peripheral_names = product_config.get_peripheral_names()
        config.peripheral_count = len(config.peripheral_names)
        
        # Digital Inputs
        config.digital_input_names = product_config.get_digital_input_names()
        config.digital_input_count = len(config.digital_input_names)
        
        # Relays
        config.relay_names = product_config.get_relay_names()
        config.relay_count = len(config.relay_names)
        
        # Clock thresholds
        clock_config = product_config.get_clock_config()
        config.clock_min_hz = clock_config.min_hz
        config.clock_max_hz = clock_config.max_hz
        config.clock_nominal_hz = clock_config.nominal_hz
        
        print(f"[TLV] Parser configured from JSON:")
        print(f"      Peripherals: {config.peripheral_count} ({config.peripheral_bytes} bytes)")
        print(f"      Digital Inputs: {config.digital_input_count} ({config.digital_input_bytes} bytes)")
        print(f"      Relays: {config.relay_count} ({config.relay_bytes} bytes)")
        print(f"      Clock: {config.clock_min_hz}-{config.clock_max_hz} Hz")
        
        return cls(config)
    
    def set_strict_validation(self, enabled: bool):
        """Enable or disable strict validation mode"""
        self._strict_validation = enabled
    
    # ========================================================================
    # CORE TLV PARSING
    # ========================================================================
    
    def parse_tlv_data(self, data: bytes) -> List[TlvElement]:
        """
        Parse raw TLV data into list of TlvElement.
        
        Args:
            data: Raw TLV payload bytes
            
        Returns:
            List of parsed TlvElement objects
            
        Raises:
            UnknownTagError: If unknown tag is encountered
            TlvParseError: If parsing fails
        """
        elements = []
        index = 0
        
        while index < len(data):
            # Check minimum bytes for tag + length
            if index + 2 > len(data):
                raise TlvParseError(f"Incomplete TLV at index {index}: missing length byte")
            
            tag = data[index]
            length = data[index + 1]
            
            # Validate tag is known
            if tag not in KNOWN_TLV_TAGS:
                raise UnknownTagError(tag)
            
            # Check value bytes available
            if index + 2 + length > len(data):
                raise TlvParseError(
                    f"Incomplete TLV at index {index}: "
                    f"expected {length} value bytes, only {len(data) - index - 2} available"
                )
            
            value = data[index + 2 : index + 2 + length]
            
            elements.append(TlvElement(tag=tag, length=length, value=value))
            
            index += 2 + length
        
        return elements
    
    def parse_single_tlv(self, data: bytes) -> TlvElement:
        """
        Parse a single TLV from data.
        
        Args:
            data: Raw bytes starting with TLV
            
        Returns:
            Single TlvElement
        """
        elements = self.parse_tlv_data(data)
        if len(elements) != 1:
            raise TlvParseError(f"Expected single TLV, got {len(elements)}")
        return elements[0]
    
    # ========================================================================
    # COMBINED RESULTS PARSING
    # ========================================================================
    
    def parse_combined_results(self, data: bytes) -> ParsedResults:
        """
        Parse combined test results frame (Protocol v1.2).
        
        Expected format (24 bytes):
        - TLV1: PERIPHERALS (tag=0x01, len=2, value=2B)
        - TLV2: MEASURE_LSE (tag=0x06, len=4, value=4B)
        - TLV3: DIG_INPUTS (tag=0x04, len=8, value=8B)
        - TLV4: RELAYS (tag=0x05, len=2, value=2B)
        
        Args:
            data: TLV payload from frame (24 bytes expected)
            
        Returns:
            ParsedResults with all test data
            
        Raises:
            TlvParseError: If parsing or validation fails
            UnknownTagError: If unknown tag encountered
        """
        result = ParsedResults()
        
        # Parse all TLVs
        elements = self.parse_tlv_data(data)
        result.raw_tlvs = elements
        
        # Process each TLV
        for tlv in elements:
            if tlv.tag == TlvTag.PERIPHERALS:
                result.peripheral_bitmap = tlv.value_as_int()
                result.peripheral_byte_count = tlv.length
                
            elif tlv.tag == TlvTag.MEASURE_LSE:
                result.clock_frequency_hz = tlv.value_as_int()
                
            elif tlv.tag == TlvTag.DIG_INPUTS:
                result.digital_input_bitmap = tlv.value_as_int()
                result.digital_input_byte_count = tlv.length
                
            elif tlv.tag == TlvTag.RELAYS:
                result.relay_bitmap = tlv.value_as_int()
                result.relay_byte_count = tlv.length
        
        # Validate and interpret results
        self._validate_and_interpret(result)
        
        return result
    
    def _validate_and_interpret(self, result: ParsedResults):
        """
        Validate bitmaps against config and interpret results.
        
        Args:
            result: ParsedResults to validate and populate
            
        Raises:
            BitmapValidationError: If validation fails in strict mode
        """
        # Validate peripheral bitmap
        if self._strict_validation and self.config.peripheral_count > 0:
            max_valid = (1 << self.config.peripheral_count) - 1
            if result.peripheral_bitmap & ~max_valid:
                raise BitmapValidationError(
                    "PERIPHERALS",
                    self.config.peripheral_count,
                    result.peripheral_bitmap
                )
        
        # Interpret peripheral results
        for i, name in enumerate(self.config.peripheral_names):
            bit_value = (result.peripheral_bitmap >> i) & 1
            result.peripheral_results[name] = (bit_value == 1)
        
        # Validate digital input bitmap
        if self._strict_validation and self.config.digital_input_count > 0:
            max_valid = (1 << self.config.digital_input_count) - 1
            if result.digital_input_bitmap & ~max_valid:
                raise BitmapValidationError(
                    "DIGITAL_INPUTS",
                    self.config.digital_input_count,
                    result.digital_input_bitmap
                )
        
        # Interpret digital input results
        for i, name in enumerate(self.config.digital_input_names):
            bit_value = (result.digital_input_bitmap >> i) & 1
            result.digital_input_results[name] = (bit_value == 1)
        
        # Validate relay bitmap
        if self._strict_validation and self.config.relay_count > 0:
            max_valid = (1 << self.config.relay_count) - 1
            if result.relay_bitmap & ~max_valid:
                raise BitmapValidationError(
                    "RELAYS",
                    self.config.relay_count,
                    result.relay_bitmap
                )
        
        # Interpret relay results
        for i, name in enumerate(self.config.relay_names):
            bit_value = (result.relay_bitmap >> i) & 1
            result.relay_results[name] = (bit_value == 1)
        
        # Clock pass/fail from JIG's determination (bit 8 of peripheral bitmap)
        # Find "Clock Frequency" in peripheral names
        clock_bit_position = None
        for i, name in enumerate(self.config.peripheral_names):
            if "clock" in name.lower():
                clock_bit_position = i
                break
        
        if clock_bit_position is not None:
            result.clock_pass = result.peripheral_results.get(
                self.config.peripheral_names[clock_bit_position], False
            )
        else:
            # Fallback: check bit 8 directly (protocol default)
            result.clock_pass = bool((result.peripheral_bitmap >> 8) & 1)
    
    # ========================================================================
    # CONFIGURATION PARSING
    # ========================================================================
    
    def parse_config_tlvs(self, data: bytes) -> Dict[str, Any]:
        """
        Parse configuration TLVs (SET_CONFIG frame).
        
        Expected TLVs:
        - TAG_SERIAL_NO (0x80): 4 bytes
        - TAG_MAC_ID (0x81): 6 bytes
        - TAG_RTC_TIMESTAMP (0x82): 4 bytes
        
        Args:
            data: TLV payload from config frame
            
        Returns:
            Dictionary with 'serial_no', 'mac_id', 'rtc_timestamp'
        """
        result = {
            'serial_no': 0,
            'mac_id': 0,
            'rtc_timestamp': 0,
        }
        
        elements = self.parse_tlv_data(data)
        
        for tlv in elements:
            if tlv.tag == TlvTag.SERIAL_NO:
                result['serial_no'] = tlv.value_as_int()
                
            elif tlv.tag == TlvTag.MAC_ID:
                # MAC is 6 bytes, pad to 8 for uint64
                mac_bytes = tlv.value + b'\x00\x00'
                result['mac_id'] = int.from_bytes(mac_bytes, 'little')
                
            elif tlv.tag == TlvTag.RTC_TIMESTAMP:
                result['rtc_timestamp'] = tlv.value_as_int()
        
        return result
    
    # ========================================================================
    # PROGRAMMING ACK PARSING
    # ========================================================================
    
    def parse_prog_ack_tlvs(self, data: bytes) -> Dict[str, Any]:
        """
        Parse programming ACK TLVs.
        
        Expected TLVs:
        - TAG_FW_TYPE (0x85): 1 byte
        - TAG_RESULT_STATUS (0x86): 1 byte
        
        Args:
            data: TLV payload from PROG_ACK frame
            
        Returns:
            Dictionary with 'fw_type' and 'success'
        """
        result = {
            'fw_type': 0,
            'success': False,
        }
        
        elements = self.parse_tlv_data(data)
        
        for tlv in elements:
            if tlv.tag == TlvTag.FW_TYPE:
                result['fw_type'] = tlv.value_as_int()
                
            elif tlv.tag == TlvTag.RESULT_STATUS:
                result['success'] = (tlv.value_as_int() == 0x01)
        
        return result
    
    # ========================================================================
    # RETEST PARSING
    # ========================================================================
    
    def parse_retest_mask_tlv(self, data: bytes) -> int:
        """
        Parse retest mask TLV.
        
        Expected TLV:
        - TAG_RETEST_MASK (0x88): 4 bytes (uint32 LE)
        
        Args:
            data: TLV payload from RETEST frame
            
        Returns:
            Retest mask as uint32
        """
        elements = self.parse_tlv_data(data)
        
        for tlv in elements:
            if tlv.tag == TlvTag.RETEST_MASK:
                return tlv.value_as_int()
        
        return 0
    
    def parse_retest_ack_tlv(self, data: bytes) -> bool:
        """
        Parse retest ACK TLV.
        
        Expected TLV:
        - TAG_ACK_STATUS (0x89): 1 byte
        
        Args:
            data: TLV payload from RETEST_ACK frame
            
        Returns:
            True if acknowledged, False if rejected
        """
        elements = self.parse_tlv_data(data)
        
        for tlv in elements:
            if tlv.tag == TlvTag.ACK_STATUS:
                return tlv.value_as_int() == 0x01
        
        return False
    
    # ========================================================================
    # JIG RELAY PARSING
    # ========================================================================
    
    def parse_jig_relay_tlvs(self, data: bytes) -> Dict[str, int]:
        """
        Parse JIG relay control TLVs.
        
        Expected TLVs:
        - TAG_RELAY_ID (0x83): 1 byte
        - TAG_RELAY_STATE (0x84): 1 byte
        
        Args:
            data: TLV payload from JIG_RELAY frame
            
        Returns:
            Dictionary with 'relay_id' and 'state'
        """
        result = {
            'relay_id': 0,
            'state': 0,
        }
        
        elements = self.parse_tlv_data(data)
        
        for tlv in elements:
            if tlv.tag == TlvTag.RELAY_ID:
                result['relay_id'] = tlv.value_as_int()
                
            elif tlv.tag == TlvTag.RELAY_STATE:
                result['state'] = tlv.value_as_int()
        
        return result
    
    # ========================================================================
    # ERROR PARSING
    # ========================================================================
    
    def parse_error_tlv(self, data: bytes) -> int:
        """
        Parse error code TLV.
        
        Expected TLV:
        - TAG_ERROR_CODE (0x87): 1 byte
        
        Args:
            data: TLV payload from error frame
            
        Returns:
            Error code
        """
        elements = self.parse_tlv_data(data)
        
        for tlv in elements:
            if tlv.tag == TlvTag.ERROR_CODE:
                return tlv.value_as_int()
        
        return 0
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def get_expected_results_length(self) -> int:
        """
        Calculate expected combined results data length from config.
        
        Returns:
            Expected TLV payload length in bytes
        """
        # Use protocol standard sizes (2, 4, 8, 2) for compatibility
        # Even if JSON has fewer items, protocol sends fixed sizes
        return COMBINED_RESULTS_DATA_LENGTH
    
    def get_bitmap_summary(self) -> Dict[str, Any]:
        """
        Get summary of bitmap configuration.
        
        Returns:
            Dictionary with bitmap sizes and counts
        """
        return {
            'peripheral_count': self.config.peripheral_count,
            'peripheral_bytes': self.config.peripheral_bytes,
            'digital_input_count': self.config.digital_input_count,
            'digital_input_bytes': self.config.digital_input_bytes,
            'relay_count': self.config.relay_count,
            'relay_bytes': self.config.relay_bytes,
            'clock_range': (self.config.clock_min_hz, self.config.clock_max_hz),
        }


# ============================================================================
# TLV BUILDER FUNCTIONS
# ============================================================================

def build_tlv(tag: int, value: bytes) -> bytes:
    """
    Build a single TLV element.
    
    Args:
        tag: TLV tag (1 byte)
        value: TLV value bytes
        
    Returns:
        Complete TLV bytes (tag + length + value)
    """
    return bytes([tag, len(value)]) + value


def build_tlv_uint8(tag: int, value: int) -> bytes:
    """Build TLV with 1-byte unsigned int value"""
    return build_tlv(tag, bytes([value & 0xFF]))


def build_tlv_uint16_le(tag: int, value: int) -> bytes:
    """Build TLV with 2-byte unsigned int value (Little Endian)"""
    return build_tlv(tag, struct.pack('<H', value & 0xFFFF))


def build_tlv_uint32_le(tag: int, value: int) -> bytes:
    """Build TLV with 4-byte unsigned int value (Little Endian)"""
    return build_tlv(tag, struct.pack('<I', value & 0xFFFFFFFF))


def build_tlv_mac(tag: int, mac_int: int) -> bytes:
    """Build TLV with 6-byte MAC address (Little Endian)"""
    mac_bytes = struct.pack('<Q', mac_int)[:6]  # Take lower 6 bytes
    return build_tlv(tag, mac_bytes)


# ============================================================================
# SINGLETON INSTANCE (will be configured from ProductConfig)
# ============================================================================
_tlv_parser_instance: Optional[TlvParser] = None


def get_tlv_parser() -> TlvParser:
    """Get the global TLV parser instance"""
    global _tlv_parser_instance
    if _tlv_parser_instance is None:
        _tlv_parser_instance = TlvParser()
    return _tlv_parser_instance


def configure_tlv_parser(product_config) -> TlvParser:
    """
    Configure the global TLV parser from product config.
    
    Args:
        product_config: ProductConfig instance
        
    Returns:
        Configured TlvParser instance
    """
    global _tlv_parser_instance
    _tlv_parser_instance = TlvParser.from_product_config(product_config)
    return _tlv_parser_instance
