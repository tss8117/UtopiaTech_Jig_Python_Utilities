# ============================================================================
# JIG ONE v1.1 - QR Scanner Service
# ============================================================================
# Handles keyboard input from QR/barcode scanners
# ============================================================================

from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum, auto


class ScanType(Enum):
    """Type of scanned code"""
    SERIAL_NUMBER = auto()
    MAC_ID = auto()
    UNKNOWN = auto()


@dataclass
class ScanResult:
    """Result of a QR scan"""
    scan_type: ScanType
    value: str
    raw: str


class QRScannerHandler:
    """
    Handles keyboard input from QR/barcode scanners.
    
    Supported formats:
    - Serial Number: 8-digit numeric (e.g., "32999999")
    - MAC ID: "M" prefix + 16 chars, MAC at positions 4-16 (e.g., "MXXX_AABBCCDDEEFF")
    """
    
    def __init__(self):
        self._buffer: str = ""
        
        # Callbacks
        self._on_serial_scanned: Optional[Callable[[str], None]] = None
        self._on_mac_scanned: Optional[Callable[[str], None]] = None
        self._on_unknown_scanned: Optional[Callable[[str], None]] = None
        # self._on_duplicate_serial: Optional[Callable[[str], None]] = None
        
        # External validation callback (for checking if serial exists)
        self._check_serial_exists: Optional[Callable[[str], str]] = None
    
    def handle_keypress(self, char: str) -> Optional[ScanResult]:
        """
        Handle a keypress event from keyboard/scanner.
        
        Args:
            char: Character received
            
        Returns:
            ScanResult if a complete scan was detected, None otherwise
        """
        self._buffer += char
        
        # Check for end of scan (carriage return)
        if self._buffer.endswith('\r'):
            scan = self._buffer.rstrip('\r')
            self._buffer = ""
            
            result = self._parse_scan(scan)
            self._handle_result(result)
            return result
        
        return None
    
    def _parse_scan(self, scan: str) -> ScanResult:
        """Parse a complete scan and determine its type"""
        raw = scan
        print(f"Debug: Parsing scan '{scan}'")
        # Check for Serial Number (8 digits)
        if len(scan) == 8 and scan.isdigit():
            return ScanResult(ScanType.SERIAL_NUMBER, scan, raw)
        
        # Check for MAC ID (M + 16 chars, MAC at 4-16)
        if scan.startswith("MAC:") :
            mac = scan[4:16]  # Extract MAC from positions 4-16
            return ScanResult(ScanType.MAC_ID, mac, raw)
        
        # Unknown format
        return ScanResult(ScanType.UNKNOWN, scan, raw)
    
    def _handle_result(self, result: ScanResult):
        """Handle parsed scan result"""
        if result.scan_type == ScanType.SERIAL_NUMBER:
            # Check if serial exists (if validation callback is set)
            # if self._check_serial_exists:
            #     state = self._check_serial_exists(result.value)
            #     if state in ["SET", "NOT_SET"]:
            #         # Serial exists, notify duplicate
            #         if self._on_duplicate_serial:
            #             self._on_duplicate_serial(result.value)
            #         return
            
            # New serial
            if self._on_serial_scanned:
                self._on_serial_scanned(result.value)
                
        elif result.scan_type == ScanType.MAC_ID:
            if self._on_mac_scanned:
                self._on_mac_scanned(result.value)
                
        else:
            if self._on_unknown_scanned:
                self._on_unknown_scanned(result.value)
    
    def clear_buffer(self):
        """Clear the input buffer"""
        self._buffer = ""
    
    # ========================================================================
    # CALLBACKS
    # ========================================================================
    
    def on_serial_scanned(self, callback: Callable[[str], None]):
        """Register callback for serial number scans"""
        self._on_serial_scanned = callback
    
    def on_mac_scanned(self, callback: Callable[[str], None]):
        """Register callback for MAC ID scans"""
        self._on_mac_scanned = callback
    
    def on_unknown_scanned(self, callback: Callable[[str], None]):
        """Register callback for unknown scans"""
        self._on_unknown_scanned = callback
    
    def on_duplicate_serial(self, callback: Callable[[str], None]):
        """Register callback for duplicate serial detection"""
        self._on_duplicate_serial = callback
    
    def set_serial_validator(self, callback: Callable[[str], str]):
        """
        Set callback to validate if serial exists.
        
        Callback should return:
        - 'SET' if serial exists and config was set
        - 'NOT_SET' if serial exists but config not set
        - 'NOT_FOUND' if serial doesn't exist
        """
        self._check_serial_exists = callback


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================
qr_scanner = QRScannerHandler()
