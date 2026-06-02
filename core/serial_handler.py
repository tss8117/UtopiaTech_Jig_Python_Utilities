# ============================================================================
# JIG ONE v1.1 - Serial Handler
# ============================================================================
# Manages RS485 serial communication with thread-safe operations
# ============================================================================

import serial
import serial.tools.list_ports
from threading import Thread, Lock, Event
from queue import Queue, Empty
from typing import Optional, List, Callable, Tuple
from dataclasses import dataclass
import time

from config.constants import (
    START_BYTE,
    END_BYTE,
    FrameIndex,
    DeviceAddress,
)
from config.settings import (
    SERIAL_BAUDRATE,
    SERIAL_TIMEOUT,
)
from core.protocol import RS485Frame, ProtocolHandler


@dataclass
class SerialPortInfo:
    """Information about a serial port"""
    device: str
    product: str
    description: str
    
    @property
    def display_name(self) -> str:
        if self.product and self.product != 'n/a':
            return f"{self.device} | {self.product}"
        return self.device


class SerialHandler:
    """
    Handles RS485 serial communication for JIG ONE.
    
    Features:
    - Thread-safe read/write operations
    - Automatic frame detection and parsing
    - Callback-based message handling
    - Connection state management
    """
    
    def __init__(self):
        self._serial: Optional[serial.Serial] = None
        self._lock = Lock()
        self._rx_thread: Optional[Thread] = None
        self._stop_event = Event()
        
        # Receive buffer
        self._rx_buffer: List[int] = []
        
        # Message queue for parsed frames
        self._frame_queue: Queue[RS485Frame] = Queue()
        
        # Callbacks
        self._on_frame_received: Optional[Callable[[RS485Frame], None]] = None
        self._on_connect: Optional[Callable[[], None]] = None
        self._on_disconnect: Optional[Callable[[], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        
        # Debug callback for raw data
        self._on_raw_rx: Optional[Callable[[bytes], None]] = None
    
    # ========================================================================
    # CONNECTION MANAGEMENT
    # ========================================================================
    
    @staticmethod
    def list_ports() -> List[SerialPortInfo]:
        """
        List available serial ports.
        
        Returns:
            List of SerialPortInfo for available ports
        """
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append(SerialPortInfo(
                device=str(port.device),
                product=str(port.product) if port.product else '',
                description=str(port.description) if port.description else ''
            ))
        return ports
    
    def connect(self, port: str, baudrate: int = None) -> bool:
        """
        Connect to serial port.
        
        Args:
            port: Serial port device path (e.g., '/dev/ttyUSB0')
            baudrate: Baud rate (default from settings)
            
        Returns:
            True if connected successfully
        """
        if baudrate is None:
            baudrate = SERIAL_BAUDRATE
        
        try:
            with self._lock:
                if self._serial and self._serial.is_open:
                    self._serial.close()
                
                self._serial = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    timeout=SERIAL_TIMEOUT
                )
                
                self._rx_buffer.clear()
                self._stop_event.clear()
            
            # Start receive thread
            self._rx_thread = Thread(target=self._receive_loop, daemon=True)
            self._rx_thread.start()
            
            if self._on_connect:
                self._on_connect()
            
            print(f"[SERIAL] Connected to {port} @ {baudrate} baud")
            return True
            
        except Exception as e:
            error_msg = f"Failed to connect to {port}: {e}"
            print(f"[SERIAL] {error_msg}")
            if self._on_error:
                self._on_error(error_msg)
            return False
    
    def disconnect(self):
        """Disconnect from serial port"""
        self._stop_event.set()
        
        with self._lock:
            if self._serial and self._serial.is_open:
                self._serial.close()
                print("[SERIAL] Disconnected")
        
        if self._rx_thread and self._rx_thread.is_alive():
            self._rx_thread.join(timeout=2.0)
        
        self._rx_buffer.clear()
        
        if self._on_disconnect:
            self._on_disconnect()
    
    @property
    def is_connected(self) -> bool:
        """Check if serial port is connected"""
        with self._lock:
            return self._serial is not None and self._serial.is_open
    
    @property
    def port_name(self) -> Optional[str]:
        """Get connected port name"""
        with self._lock:
            if self._serial:
                return self._serial.port
        return None
    
    # ========================================================================
    # DATA TRANSMISSION
    # ========================================================================
    
    def write(self, data: bytes) -> bool:
        """
        Write data to serial port (thread-safe).
        
        Args:
            data: Bytes to send
            
        Returns:
            True if sent successfully
        """
        with self._lock:
            if not self._serial or not self._serial.is_open:
                return False
            
            try:
                self._serial.write(data)
                # Debug output
                hex_str = ' '.join(f'{b:02X}' for b in data)
                print(f"[TX] {hex_str}")
                return True
            except Exception as e:
                print(f"[SERIAL] Write error: {e}")
                if self._on_error:
                    self._on_error(f"Write error: {e}")
                return False
    
    def write_frame(self, frame: bytearray) -> bool:
        """
        Write a complete frame to serial port.
        
        Args:
            frame: Frame bytearray (built by ProtocolHandler)
            
        Returns:
            True if sent successfully
        """
        return self.write(bytes(frame))
    
    # ========================================================================
    # RECEIVE HANDLING
    # ========================================================================
    
    def _receive_loop(self):
        """Background thread for receiving serial data"""
        print("[SERIAL] Receive loop started")
        
        while not self._stop_event.is_set():
            try:
                with self._lock:
                    if not self._serial or not self._serial.is_open:
                        break
                    
                    waiting = self._serial.in_waiting
                    if waiting > 0:
                        data = self._serial.read(waiting)
                        self._rx_buffer.extend(data)
                        
                        # Debug: raw RX
                        if self._on_raw_rx:
                            self._on_raw_rx(data)
                        
                        hex_str = ' '.join(f'{b:02X}' for b in data)
                        print(f"[RX] {waiting} bytes: {hex_str}")
                
                # Process buffer outside lock
                self._process_buffer()
                
                # Small delay to prevent CPU spinning
                time.sleep(0.01)
                
            except Exception as e:
                print(f"[SERIAL] Receive error: {e}")
                if self._on_error:
                    self._on_error(f"Receive error: {e}")
                break
        
        print("[SERIAL] Receive loop ended")
    
    def _process_buffer(self):
        """Process receive buffer and extract complete frames"""
        while len(self._rx_buffer) >= 6:  # Minimum frame size
            # Look for start byte
            if self._rx_buffer[0] != START_BYTE:
                # Discard byte and continue
                self._rx_buffer.pop(0)
                continue
            
            # Check if we have enough bytes to read length
            if len(self._rx_buffer) < 4:
                break
            
            data_length = self._rx_buffer[FrameIndex.DATA_LENGTH]
            end_byte_index = FrameIndex.DATA_LENGTH + data_length + 1
            
            # Check if we have complete frame
            if len(self._rx_buffer) <= end_byte_index:
                break
            
            # Check end byte
            if self._rx_buffer[end_byte_index] != END_BYTE:
                # Invalid frame, discard start byte and continue
                print(f"[SERIAL] Invalid frame end byte: 0x{self._rx_buffer[end_byte_index]:02X}")
                self._rx_buffer.pop(0)
                continue
            
            # Parse the frame
            result = ProtocolHandler.parse_frame(self._rx_buffer)
            if result:
                frame, consumed = result
                
                # Remove consumed bytes from buffer
                del self._rx_buffer[:consumed]
                
                # Debug output
                print(f"[FRAME] {frame}")
                
                # Queue frame and call callback
                self._frame_queue.put(frame)
                
                if self._on_frame_received:
                    self._on_frame_received(frame)
            else:
                # Failed to parse, discard start byte
                self._rx_buffer.pop(0)
    
    def get_frame(self, timeout: float = 0.0) -> Optional[RS485Frame]:
        """
        Get next received frame from queue.
        
        Args:
            timeout: Timeout in seconds (0 = non-blocking)
            
        Returns:
            RS485Frame or None if no frame available
        """
        try:
            return self._frame_queue.get(block=(timeout > 0), timeout=timeout)
        except Empty:
            return None
    
    def clear_rx_buffer(self):
        """Clear receive buffer and frame queue"""
        self._rx_buffer.clear()
        while not self._frame_queue.empty():
            try:
                self._frame_queue.get_nowait()
            except Empty:
                break
    
    # ========================================================================
    # CALLBACKS
    # ========================================================================
    
    def on_frame_received(self, callback: Callable[[RS485Frame], None]):
        """Register callback for received frames"""
        self._on_frame_received = callback
    
    def on_connect(self, callback: Callable[[], None]):
        """Register callback for connection"""
        self._on_connect = callback
    
    def on_disconnect(self, callback: Callable[[], None]):
        """Register callback for disconnection"""
        self._on_disconnect = callback
    
    def on_error(self, callback: Callable[[str], None]):
        """Register callback for errors"""
        self._on_error = callback
    
    def on_raw_rx(self, callback: Callable[[bytes], None]):
        """Register callback for raw received data (debug)"""
        self._on_raw_rx = callback
    
    # ========================================================================
    # UTILITY
    # ========================================================================
    
    def flush(self):
        """Flush serial buffers"""
        with self._lock:
            if self._serial and self._serial.is_open:
                self._serial.reset_input_buffer()
                self._serial.reset_output_buffer()
        self._rx_buffer.clear()


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================
# Global serial handler instance for the application
serial_handler = SerialHandler()
