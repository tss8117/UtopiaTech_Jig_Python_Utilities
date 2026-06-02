# ============================================================================
# JIG ONE v1.2 - RS485 Protocol Handler
# ============================================================================
# Frame Format: 0x7D | FROM | TO | LEN | TLV_DATA... | 0xD9
# TLV Format: TAG (1B) | LENGTH (1B) | VALUE (LEN bytes)
# ============================================================================

import struct
from typing import Optional, Tuple, List
from dataclasses import dataclass

from config.constants import (
    START_BYTE,
    END_BYTE,
    FrameIndex,
    DeviceAddress,
    TlvTag,
    JigRelayID,
    RelayState,
    FirmwareType,
    RetestMask,
    ErrorCode,
    ProgStatus,  # Added import for ProgStatus
)
from core.tlv_parser import (
    TlvParser,
    TlvElement,
    ParsedResults,
    build_tlv,
    build_tlv_uint8,
    build_tlv_uint16_le,
    build_tlv_uint32_le,
    build_tlv_mac,
    get_tlv_parser,
)


@dataclass
class RS485Frame:
    """Parsed RS485 frame with TLV payload"""
    from_addr: int
    to_addr: int
    data_length: int
    tlv_data: bytes
    raw: bytes
    
    # Parsed TLV elements (populated after parsing)
    tlv_elements: List[TlvElement] = None
    
    @property
    def first_tag(self) -> Optional[int]:
        """Get the first TLV tag (for command identification)"""
        if self.tlv_data and len(self.tlv_data) >= 1:
            return self.tlv_data[0]
        return None
    
    def __repr__(self):
        tag_str = f"0x{self.first_tag:02X}" if self.first_tag else "None"
        return (f"RS485Frame(from=0x{self.from_addr:02X}, to=0x{self.to_addr:02X}, "
                f"len={self.data_length}, first_tag={tag_str})")


class ProtocolHandler:
    """
    Handles RS485 protocol frame building and parsing.
    Implements JIG ONE Protocol v1.2 with TLV format.
    """
    
    # ========================================================================
    # FRAME BUILDING (Base)
    # ========================================================================
    
    @staticmethod
    def build_frame(from_addr: int, to_addr: int, tlv_payload: bytes) -> bytearray:
        """
        Build an RS485 frame with TLV payload.
        
        Args:
            from_addr: Source device address
            to_addr: Destination device address
            tlv_payload: Complete TLV data (one or more TLVs concatenated)
            
        Returns:
            Complete frame as bytearray
        """
        data_length = len(tlv_payload)
        frame = bytearray([
            START_BYTE,
            from_addr,
            to_addr,
            data_length,
        ])
        frame.extend(tlv_payload)
        frame.append(END_BYTE)
        return frame
    
    # ========================================================================
    # RASPI → JIG COMMANDS (TLV Format)
    # ========================================================================
    
    @staticmethod
    def build_start_prog_ack(status: int = 0x01) -> bytearray:
        """
        Build START_PROG acknowledgment frame.
        RASPi → JIG: Acknowledge start programming request
        
        TLV: TAG_START_PROG (0xEA) | 0x01 | STATUS
        
        Args:
            status: 0x00 = Ready (button pressed), 0x01 = Starting (acknowledged)
        """
        tlv = build_tlv_uint8(TlvTag.START_PROG, status)
        return ProtocolHandler.build_frame(
            DeviceAddress.RASPI,
            DeviceAddress.JIG_BOARD,
            tlv
        )
    
    @staticmethod
    def build_prog_status(prog_status: ProgStatus) -> bytearray:
        """
        Build programming status frame (final result).
        RASPi → JIG: Report programming completion status

        TLV: TAG_PROG_STATUS (0x8A) | 0x01 | STATUS

        Args:
            prog_status: ProgStatus enum value
                - IDLE (0x00): Not programming
                - SUCCESS (0x01): Programming successful
                - FAILED (0x02): Programming failed
                - NO_SCAN (0x03): No QR code scanned
                - NO_FILES (0x04): Firmware files not found
                - TIMEOUT (0x05): Programming timeout
                - RETRY (0x06): Retry in progress
        """
        tlv = build_tlv_uint8(TlvTag.START_PROG, prog_status)
        return ProtocolHandler.build_frame(
            DeviceAddress.RASPI,
            DeviceAddress.JIG_BOARD,
            tlv
        )

    @staticmethod
    def build_prog_ack(firmware_type: FirmwareType, success: bool) -> bytearray:
        """
        Build PROG_ACK frame (Protocol v1.2).
        RASPi → JIG: Report programming result
        
        TLVs: TAG_FW_TYPE + TAG_RESULT_STATUS
        
        Args:
            firmware_type: BOOTLOADER, TEST_CODE, or FINAL
            success: True if programming succeeded
        """
        result = 0x01 if success else 0x00
        tlv_payload = (
            build_tlv_uint8(TlvTag.FW_TYPE, firmware_type) +
            build_tlv_uint8(TlvTag.RESULT_STATUS, result)
        )
        return ProtocolHandler.build_frame(
            DeviceAddress.RASPI,
            DeviceAddress.JIG_BOARD,
            tlv_payload
        )
    
    @staticmethod
    def build_prog_final_ack(status: int = 0x02) -> bytearray:
        """
        Build PROG_FINAL acknowledgment frame.
        RASPi → JIG: Final firmware programming complete
        
        TLV: TAG_PROG_FINAL (0xEB) | 0x01 | STATUS
        """
        tlv = build_tlv_uint8(TlvTag.PROG_FINAL, status)
        return ProtocolHandler.build_frame(
            DeviceAddress.RASPI,
            DeviceAddress.JIG_BOARD,
            tlv
        )
    
    @staticmethod
    def build_retest_command(retest_mask: int) -> bytearray:
        """
        Build RETEST command frame (Protocol v1.2 - TLV format).
        RASPi → JIG: Request retest of specific categories
        
        TLV: TAG_RETEST_MASK (0x88) | 0x04 | MASK (4 bytes LE)
        
        Args:
            retest_mask: uint32_t bitmask (use RetestMask constants)
                         PERIPHERALS = 0x00000001
                         DIG_INPUTS = 0x00000002
                         RELAYS = 0x00000004
                         ALL = 0xFFFFFFFF
        """
        tlv = build_tlv_uint32_le(TlvTag.RETEST_MASK, retest_mask)
        return ProtocolHandler.build_frame(
            DeviceAddress.RASPI,
            DeviceAddress.JIG_BOARD,
            tlv
        )
    
    @staticmethod
    def build_jig_relay_control(relay_id: JigRelayID, state: RelayState) -> bytearray:
        """
        Build JIG_RELAY control frame (Protocol v1.2 - TLV format).
        RASPi → JIG: Control JIG board relays (LEDs, Reset)
        
        TLVs: TAG_RELAY_ID + TAG_RELAY_STATE
        
        Args:
            relay_id: RED_LED, GREEN_LED, RESET, SPARE_1, SPARE_2
            state: ON or OFF
        """
        tlv_payload = (
            build_tlv_uint8(TlvTag.RELAY_ID, relay_id) +
            build_tlv_uint8(TlvTag.RELAY_STATE, state)
        )
        return ProtocolHandler.build_frame(
            DeviceAddress.RASPI,
            DeviceAddress.JIG_BOARD,
            tlv_payload
        )
    
    @staticmethod
    def build_comm_failed(error_code: ErrorCode) -> bytearray:
        """
        Build COMM_FAILED frame.
        RASPi → JIG: Report communication error
        
        TLV: TAG_ERROR_CODE (0x87) | 0x01 | ERROR_CODE
        """
        tlv = build_tlv_uint8(TlvTag.ERROR_CODE, error_code)
        return ProtocolHandler.build_frame(
            DeviceAddress.RASPI,
            DeviceAddress.JIG_BOARD,
            tlv
        )
    
    # ========================================================================
    # RASPI → DUT COMMANDS (TLV Format)
    # ========================================================================
    
    @staticmethod
    def build_set_config(serial_no: int, mac_id: int, rtc_timestamp: int) -> bytearray:
        """
        Build SET_CONFIG frame (Protocol v1.2 - TLV format).
        RASPi → DUT: Set device configuration
        
        TLVs: TAG_SERIAL_NO + TAG_MAC_ID + TAG_RTC_TIMESTAMP
        
        Args:
            serial_no: 4-byte serial number (e.g., 32999999)
            mac_id: 6-byte MAC address as int (e.g., 0xAABBCCDDEEFF)
            rtc_timestamp: 4-byte Unix timestamp
        """
        tlv_payload = (
            build_tlv_uint32_le(TlvTag.SERIAL_NO, serial_no) +
            build_tlv_mac(TlvTag.MAC_ID, mac_id) +
            build_tlv_uint32_le(TlvTag.RTC_TIMESTAMP, rtc_timestamp)
        )
        return ProtocolHandler.build_frame(
            DeviceAddress.RASPI,
            DeviceAddress.DUT,
            tlv_payload
        )
    
    # ========================================================================
    # FRAME PARSING
    # ========================================================================
    
    @staticmethod
    def parse_frame(buffer: List[int]) -> Optional[Tuple[RS485Frame, int]]:
        """
        Parse an RS485 frame from buffer.
        
        Args:
            buffer: List of received bytes
            
        Returns:
            Tuple of (parsed frame, bytes consumed) or None if incomplete/invalid
        """
        MIN_FRAME_SIZE = 7  # v1.2 minimum: Header(4) + TLV(2) + Footer(1)
        
        if len(buffer) < MIN_FRAME_SIZE:
            return None
        
        # Check start byte
        if buffer[FrameIndex.HEADER] != START_BYTE:
            return None
        
        # Get data length
        data_length = buffer[FrameIndex.DATA_LENGTH]
        end_byte_index = FrameIndex.DATA_LENGTH + data_length + 1
        
        # Check if we have enough bytes
        if len(buffer) <= end_byte_index:
            return None
        
        # Check end byte
        if buffer[end_byte_index] != END_BYTE:
            return None
        
        # Extract frame components
        from_addr = buffer[FrameIndex.FROM_ADDR]
        to_addr = buffer[FrameIndex.TO_ADDR]
        tlv_data = bytes(buffer[FrameIndex.DATA_START:end_byte_index])
        raw = bytes(buffer[:end_byte_index + 1])
        
        frame = RS485Frame(
            from_addr=from_addr,
            to_addr=to_addr,
            data_length=data_length,
            tlv_data=tlv_data,
            raw=raw
        )
        
        return (frame, end_byte_index + 1)
    
    # ========================================================================
    # TLV PAYLOAD PARSING HELPERS
    # ========================================================================
    
    @staticmethod
    def parse_combined_results(tlv_data: bytes) -> ParsedResults:
        """
        Parse combined test results from TLV payload.
        
        Args:
            tlv_data: TLV payload from combined results frame
            
        Returns:
            ParsedResults with all test data
        """
        parser = get_tlv_parser()
        return parser.parse_combined_results(tlv_data)
    
    @staticmethod
    def parse_config_echo(tlv_data: bytes) -> Tuple[int, int, int]:
        """
        Parse configuration echo TLVs from DUT.
        
        Args:
            tlv_data: TLV payload from config echo frame
            
        Returns:
            Tuple of (serial_no, mac_id, rtc_timestamp)
        """
        parser = get_tlv_parser()
        result = parser.parse_config_tlvs(tlv_data)
        return (result['serial_no'], result['mac_id'], result['rtc_timestamp'])
    
    @staticmethod
    def parse_prog_ack(tlv_data: bytes) -> Tuple[int, bool]:
        """
        Parse programming ACK TLVs.
        
        Args:
            tlv_data: TLV payload from PROG_ACK frame
            
        Returns:
            Tuple of (firmware_type, success)
        """
        parser = get_tlv_parser()
        result = parser.parse_prog_ack_tlvs(tlv_data)
        return (result['fw_type'], result['success'])
    
    @staticmethod
    def parse_retest_ack(tlv_data: bytes) -> bool:
        """
        Parse retest acknowledgment TLV.
        
        Args:
            tlv_data: TLV payload from RETEST_ACK frame
            
        Returns:
            True if acknowledged, False if rejected
        """
        parser = get_tlv_parser()
        return parser.parse_retest_ack_tlv(tlv_data)
    
    @staticmethod
    def parse_start_prog(tlv_data: bytes) -> int:
        """
        Parse START_PROG TLV.
        
        Args:
            tlv_data: TLV payload from START_PROG frame
            
        Returns:
            Status byte (0x00 = button pressed, 0x01 = acknowledged)
        """
        if len(tlv_data) >= 3:
            tag = tlv_data[0]
            length = tlv_data[1]
            if tag == TlvTag.START_PROG and length >= 1:
                return tlv_data[2]
        return 0
    
    @staticmethod
    def parse_error_code(tlv_data: bytes) -> int:
        """
        Parse error code TLV.
        
        Args:
            tlv_data: TLV payload from error frame
            
        Returns:
            Error code
        """
        parser = get_tlv_parser()
        return parser.parse_error_tlv(tlv_data)
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    @staticmethod
    def frame_to_hex_string(frame: bytearray) -> str:
        """Convert frame to hex string for debugging"""
        return ' '.join(f'{b:02X}' for b in frame)
    
    @staticmethod
    def get_tag_name(tag: int) -> str:
        """Get human-readable tag name"""
        try:
            return TlvTag(tag).name
        except ValueError:
            return f"UNKNOWN(0x{tag:02X})"
    
    @staticmethod
    def get_device_name(addr: int) -> str:
        """Get human-readable device name"""
        try:
            return DeviceAddress(addr).name
        except ValueError:
            return f"UNKNOWN(0x{addr:02X})"
    
    @staticmethod
    def is_combined_results_frame(frame: RS485Frame) -> bool:
        """
        Check if frame is a combined results frame.
        
        In v1.2, combined results contain multiple TLVs starting with
        TAG_PERIPHERALS (0x01).
        
        Args:
            frame: Parsed RS485Frame
            
        Returns:
            True if this is a combined results frame
        """
        if frame.from_addr != DeviceAddress.JIG_BOARD:
            return False
        if frame.first_tag != TlvTag.PERIPHERALS:
            return False
        # Combined results should be ~24 bytes (may vary slightly)
        if frame.data_length < 20:
            return False
        return True


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def build_dut_reset_pulse() -> Tuple[bytearray, bytearray]:
    """
    Build frames for DUT reset pulse.
    
    Returns:
        Tuple of (reset_on_frame, reset_off_frame)
    """
    reset_on = ProtocolHandler.build_jig_relay_control(
        JigRelayID.RESET, RelayState.ON
    )
    reset_off = ProtocolHandler.build_jig_relay_control(
        JigRelayID.RESET, RelayState.OFF
    )
    return (reset_on, reset_off)


def build_led_control(pass_result: bool) -> bytearray:
    """
    Build frame to turn on appropriate LED based on result.
    
    Args:
        pass_result: True for green LED, False for red LED
    """
    if pass_result:
        return ProtocolHandler.build_jig_relay_control(
            JigRelayID.GREEN_LED, RelayState.ON
        )
    else:
        return ProtocolHandler.build_jig_relay_control(
            JigRelayID.RED_LED, RelayState.ON
        )


def build_all_leds_off() -> List[bytearray]:
    """
    Build frames to turn off all indicator LEDs.
    
    Returns:
        List of frames to send
    """
    return [
        ProtocolHandler.build_jig_relay_control(JigRelayID.RED_LED, RelayState.OFF),
        ProtocolHandler.build_jig_relay_control(JigRelayID.GREEN_LED, RelayState.OFF),
    ]
