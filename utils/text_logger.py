# ============================================================================
# JIG ONE v1.1 - Text Logger (Tier 2)
# ============================================================================
# Per-DUT detailed text log files
# ============================================================================

import os
from datetime import datetime
from typing import Optional, TextIO

from config.settings import (
    TEST_LOGS_DIR,
    DEVELOPER_MODE_ENABLED,
)
from config.constants import VERSION


class TextLogger:
    """
    Tier 2 Logging: Per-DUT detailed text log files.
    
    Features:
    - One file per DUT test session
    - Timestamped entries
    - Section headers
    - Test summary
    """
    
    def __init__(self, log_dir: str = None):
        """
        Initialize text logger.
        
        Args:
            log_dir: Directory for log files (default: Test_Logs/)
        """
        self.log_dir = log_dir or TEST_LOGS_DIR
        os.makedirs(self.log_dir, exist_ok=True)
        
        self._file_handle: Optional[TextIO] = None
        self._current_serial: str = ""
        self._session_start: Optional[datetime] = None
    
    def start_session(self, serial_no: str, mac_id: str):
        """
        Start a new test session log.
        
        Args:
            serial_no: Device serial number
            mac_id: Device MAC ID
        """
        # Close any existing session
        self.end_session()
        
        self._current_serial = serial_no
        self._session_start = datetime.now()
        
        # Create log file
        timestamp = self._session_start.strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{serial_no}_{timestamp}.txt"
        filepath = os.path.join(self.log_dir, filename)
        
        self._file_handle = open(filepath, 'w')
        
        # Write header
        self._write_line("=" * 80)
        self._write_line("JIG ONE - TEST LOG")
        self._write_line("=" * 80)
        self._write_line(f"Serial No.  : {serial_no}")
        self._write_line(f"MAC ID      : {mac_id}")
        self._write_line(f"Date        : {self._session_start.strftime('%Y-%m-%d')}")
        self._write_line(f"Start Time  : {self._session_start.strftime('%H:%M:%S')}")
        self._write_line(f"Mode        : {'DEVELOPER' if DEVELOPER_MODE_ENABLED else 'USER'}")
        self._write_line(f"Utility Ver : {VERSION}")
        self._write_line("=" * 80)
        self._write_line("")
        
        print(f"[LOG] Started session: {filepath}")
    
    def log(self, level: str, message: str):
        """
        Log a message with timestamp.
        
        Args:
            level: Log level (INFO, ERROR, OK, TEST, etc.)
            message: Message to log
        """
        if self._file_handle:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self._write_line(f"[{timestamp}] {level:5} | {message}")
    
    def log_section(self, title: str):
        """
        Log a section header.
        
        Args:
            title: Section title
        """
        if self._file_handle:
            self._write_line("")
            self._write_line("-" * 80)
            self._write_line(title)
            self._write_line("-" * 80)
    
    def log_test_result(self, test_name: str, passed: bool):
        """
        Log a single test result.
        
        Args:
            test_name: Name of the test
            passed: True if passed, False if failed
        """
        status = "PASS" if passed else "FAIL"
        padding = "." * (30 - len(test_name))
        self.log("TEST", f"{test_name}{padding} {status}")
    
    def end_session(
        self,
        total: int = 0,
        passed: int = 0,
        failed: int = 0,
        retries: int = 0,
        result: str = ""
    ):
        """
        End the current test session.
        
        Args:
            total: Total number of tests
            passed: Number of passed tests
            failed: Number of failed tests
            retries: Number of retry attempts used
            result: Final result string (PASS/FAIL)
        """
        if self._file_handle:
            # Write summary if data provided
            if total > 0:
                self._write_line("")
                self._write_line("=" * 80)
                self._write_line("TEST SUMMARY")
                self._write_line("=" * 80)
                self._write_line(f"Total Tests    : {total}")
                self._write_line(f"Passed         : {passed}")
                self._write_line(f"Failed         : {failed}")
                self._write_line(f"Retries Used   : {retries}")
                self._write_line(f"Final Result   : {result}")
                self._write_line(f"End Time       : {datetime.now().strftime('%H:%M:%S')}")
                
                if self._session_start:
                    duration = datetime.now() - self._session_start
                    self._write_line(f"Duration       : {duration}")
                
                self._write_line("=" * 80)
            
            # Close file
            self._file_handle.close()
            self._file_handle = None
            
            print(f"[LOG] Ended session for {self._current_serial}")
        
        self._current_serial = ""
        self._session_start = None
    
    def _write_line(self, text: str):
        """Write a line to the log file"""
        if self._file_handle:
            self._file_handle.write(text + "\n")
            self._file_handle.flush()
    
    @property
    def is_active(self) -> bool:
        """Check if a session is active"""
        return self._file_handle is not None
    
    @property
    def current_serial(self) -> str:
        """Get current session serial number"""
        return self._current_serial


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================
text_logger = TextLogger()
