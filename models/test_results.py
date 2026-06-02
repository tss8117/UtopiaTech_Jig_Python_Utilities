# ============================================================================
# JIG ONE v1.2 - Test Results Model
# ============================================================================
# Manages test results with attempt tracking and TLV parser integration
# ============================================================================

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from core.tlv_parser import ParsedResults


class TestResult(Enum):
    """Individual test result status"""
    NOT_TESTED = 0
    PASS = 1
    FAIL = 2
    PENDING = 3


@dataclass
class TestItem:
    """Single test item with result"""
    name: str
    bit_position: int
    result: TestResult = TestResult.NOT_TESTED
    gui_element: Any = None  # Reference to GUI button
    
    @property
    def passed(self) -> bool:
        return self.result == TestResult.PASS
    
    @property
    def failed(self) -> bool:
        return self.result == TestResult.FAIL
    
    def set_from_bit(self, bit_value: int):
        """Set result from bitmap bit (1=pass, 0=fail)"""
        self.result = TestResult.PASS if bit_value == 1 else TestResult.FAIL
    
    def set_from_bool(self, passed: bool):
        """Set result from boolean"""
        self.result = TestResult.PASS if passed else TestResult.FAIL
    
    def reset(self):
        """Reset to not tested state"""
        self.result = TestResult.NOT_TESTED


@dataclass
class TestAttempt:
    """Record of a single test attempt"""
    attempt_number: int
    timestamp: datetime
    peripherals_failed: List[str] = field(default_factory=list)
    digital_inputs_failed: List[str] = field(default_factory=list)
    relays_failed: List[str] = field(default_factory=list)
    clock_frequency_hz: int = 0
    clock_pass: bool = False
    config_state: str = "NOT SET"  # "SET" or "NOT SET"
    overall_pass: bool = False
    
    def __post_init__(self):
        self.overall_pass = (
            len(self.peripherals_failed) == 0 and
            len(self.digital_inputs_failed) == 0 and
            len(self.relays_failed) == 0
        )


class TestResultsManager:
    """
    Manages test results and converts between TLV parsed data and named results.
    Dynamically built from product configuration.
    
    New in v1.2:
    - Integration with TlvParser for combined results frame
    - Attempt tracking with separate rows
    - Clock frequency Hz tracking
    """
    
    def __init__(self, product_config):
        """
        Initialize with product configuration.
        
        Args:
            product_config: ProductConfig instance
        """
        self.product_config = product_config
        self.peripherals: Dict[str, TestItem] = {}
        self.digital_inputs: Dict[str, TestItem] = {}
        self.relays: Dict[str, TestItem] = {}
        self.additional_tests: Dict[str, TestItem] = {}
        
        self.clock_frequency_hz: int = 0
        self.clock_pass: bool = False
        self.current_attempt: int = 0
        self.config_state: str = "NOT SET"
        self.test_history: List[TestAttempt] = []
        
        self._build_test_items()
    
    def _build_test_items(self):
        """Build test item dictionaries from product config"""
        # Peripherals
        for i, name in enumerate(self.product_config.get_peripheral_names()):
            self.peripherals[name] = TestItem(name=name, bit_position=i)
        
        # Digital Inputs
        for i, name in enumerate(self.product_config.get_digital_input_names()):
            self.digital_inputs[name] = TestItem(name=name, bit_position=i)
        
        # Relays
        for i, name in enumerate(self.product_config.get_relay_names()):
            self.relays[name] = TestItem(name=name, bit_position=i)
        
        # Additional Tests (placeholder for future expansion)
        for test in self.product_config.get_additional_tests():
            if test.get("enabled", False):
                name = test["name"]
                self.additional_tests[name] = TestItem(
                    name=name,
                    bit_position=test.get("bit_position", 0)
                )
    
    # ========================================================================
    # TLV INTEGRATION (v1.2)
    # ========================================================================
    
    def apply_parsed_results(self, parsed: ParsedResults):
        """
        Apply parsed TLV results to test items.
        
        Args:
            parsed: ParsedResults from TlvParser.parse_combined_results()
        """
        # Store clock frequency
        self.clock_frequency_hz = parsed.clock_frequency_hz
        self.clock_pass = parsed.clock_pass
        
        # Apply peripheral results
        for name, passed in parsed.peripheral_results.items():
            if name in self.peripherals:
                self.peripherals[name].set_from_bool(passed)
        
        # Apply digital input results
        for name, passed in parsed.digital_input_results.items():
            if name in self.digital_inputs:
                self.digital_inputs[name].set_from_bool(passed)
        
        # Apply relay results
        for name, passed in parsed.relay_results.items():
            if name in self.relays:
                self.relays[name].set_from_bool(passed)
    
    # ========================================================================
    # LEGACY BITMAP PARSING (for backward compatibility)
    # ========================================================================
    
    def parse_peripheral_bitmap(self, bitmap: int, clock_freq: int = 0) -> List[str]:
        """
        Parse peripheral test results from bitmap.
        
        Args:
            bitmap: 2-byte bitmap (Little Endian, already converted to int)
            clock_freq: Clock frequency measurement in Hz
            
        Returns:
            List of failed peripheral names
        """
        self.clock_frequency_hz = clock_freq
        failed = []
        
        # Check clock pass/fail from bitmap (typically bit 8)
        clock_config = self.product_config.get_clock_config()
        
        for name, item in self.peripherals.items():
            bit_value = (bitmap >> item.bit_position) & 1
            item.set_from_bit(bit_value)
            if item.failed:
                failed.append(name)
            
            # Track clock pass separately
            if "clock" in name.lower():
                self.clock_pass = item.passed
        
        return failed
    
    def parse_digital_input_bitmap(self, bitmap: int) -> List[str]:
        """
        Parse digital input test results from bitmap.
        
        Args:
            bitmap: 8-byte bitmap (Little Endian, already converted to int)
            
        Returns:
            List of failed digital input names
        """
        failed = []
        
        for name, item in self.digital_inputs.items():
            bit_value = (bitmap >> item.bit_position) & 1
            item.set_from_bit(bit_value)
            if item.failed:
                failed.append(name)
        
        return failed
    
    def parse_relay_bitmap(self, bitmap: int) -> List[str]:
        """
        Parse relay test results from bitmap.
        
        Args:
            bitmap: 2-byte bitmap (Little Endian, already converted to int)
            
        Returns:
            List of failed relay names
        """
        failed = []
        
        for name, item in self.relays.items():
            bit_value = (bitmap >> item.bit_position) & 1
            item.set_from_bit(bit_value)
            if item.failed:
                failed.append(name)
        
        return failed
    
    # ========================================================================
    # TEST HISTORY / ATTEMPT TRACKING
    # ========================================================================
    
    def record_attempt(self) -> TestAttempt:
        """
        Record current test results as an attempt.
        
        Returns:
            TestAttempt record
        """
        self.current_attempt += 1
        
        attempt = TestAttempt(
            attempt_number=self.current_attempt,
            timestamp=datetime.now(),
            peripherals_failed=self.get_failed_peripherals(),
            digital_inputs_failed=self.get_failed_digital_inputs(),
            relays_failed=self.get_failed_relays(),
            clock_frequency_hz=self.clock_frequency_hz,
            clock_pass=self.clock_pass,
            config_state=self.config_state,
        )
        self.test_history.append(attempt)
        return attempt
    
    def set_config_state(self, state: str):
        """
        Set configuration state.
        
        Args:
            state: "SET" or "NOT SET"
        """
        self.config_state = state
        # Update last attempt if exists
        if self.test_history:
            self.test_history[-1].config_state = state
    
    def get_last_attempt(self) -> Optional[TestAttempt]:
        """Get the most recent test attempt"""
        return self.test_history[-1] if self.test_history else None
    
    def clear_history(self):
        """Clear all test history and reset attempt counter"""
        self.test_history.clear()
        self.current_attempt = 0
        self.config_state = "NOT SET"
    
    # ========================================================================
    # RESULT GETTERS
    # ========================================================================
    
    def get_failed_peripherals(self) -> List[str]:
        """Get list of failed peripheral names"""
        return [name for name, item in self.peripherals.items() if item.failed]
    
    def get_failed_digital_inputs(self) -> List[str]:
        """Get list of failed digital input names"""
        return [name for name, item in self.digital_inputs.items() if item.failed]
    
    def get_failed_relays(self) -> List[str]:
        """Get list of failed relay names"""
        return [name for name, item in self.relays.items() if item.failed]
    
    def get_all_failed(self) -> Dict[str, List[str]]:
        """Get all failed tests grouped by category"""
        return {
            "peripherals": self.get_failed_peripherals(),
            "digital_inputs": self.get_failed_digital_inputs(),
            "relays": self.get_failed_relays()
        }
    
    def is_all_passed(self) -> bool:
        """Check if all tests passed"""
        return (
            len(self.get_failed_peripherals()) == 0 and
            len(self.get_failed_digital_inputs()) == 0 and
            len(self.get_failed_relays()) == 0
        )
    
    def get_total_count(self) -> int:
        """Get total number of tests"""
        return len(self.peripherals) + len(self.digital_inputs) + len(self.relays)
    
    def get_pass_count(self) -> int:
        """Get number of passed tests"""
        passed = 0
        for item in self.peripherals.values():
            if item.passed:
                passed += 1
        for item in self.digital_inputs.values():
            if item.passed:
                passed += 1
        for item in self.relays.values():
            if item.passed:
                passed += 1
        return passed
    
    def get_fail_count(self) -> int:
        """Get number of failed tests"""
        return (
            len(self.get_failed_peripherals()) +
            len(self.get_failed_digital_inputs()) +
            len(self.get_failed_relays())
        )
    
    # ========================================================================
    # RESET METHODS
    # ========================================================================
    
    def reset_all(self):
        """Reset all test results (but keep history)"""
        for item in self.peripherals.values():
            item.reset()
        for item in self.digital_inputs.values():
            item.reset()
        for item in self.relays.values():
            item.reset()
        for item in self.additional_tests.values():
            item.reset()
        self.clock_frequency_hz = 0
        self.clock_pass = False
    
    def reset_for_new_test(self):
        """Reset for a completely new test (clear history too)"""
        self.reset_all()
        self.clear_history()
    
    def reset_peripherals(self):
        """Reset only peripheral results"""
        for item in self.peripherals.values():
            item.reset()
    
    def reset_digital_inputs(self):
        """Reset only digital input results"""
        for item in self.digital_inputs.values():
            item.reset()
    
    def reset_relays(self):
        """Reset only relay results"""
        for item in self.relays.values():
            item.reset()
    
    # ========================================================================
    # LOGGING DICTIONARY (for Excel)
    # ========================================================================
    
    def to_log_dict(self, serial_no: str, mac_id: str) -> Dict[str, Any]:
        """
        Convert current results to dictionary for Excel logging.
        Creates one row per attempt.
        
        Args:
            serial_no: Device serial number
            mac_id: Device MAC ID
            
        Returns:
            Dictionary ready for Excel logging
        """
        now = datetime.now()
        
        log_dict = {
            '_id': serial_no,
            'Date': now.strftime('%d-%m-%Y'),
            'Time': now.strftime('%H:%M:%S'),
            'Serial No.': serial_no,
            'MAC ID': mac_id,
            'Config State': self.config_state,
            'Attempt': self.current_attempt,
            'Clock Frequency Hz': self.clock_frequency_hz,
        }
        
        # Add peripheral results
        for name, item in self.peripherals.items():
            log_dict[name] = "PASS" if item.passed else "FAIL"
        
        # Add digital input results
        for name, item in self.digital_inputs.items():
            log_dict[name] = "PASS" if item.passed else "FAIL"
        
        # Add relay results
        for name, item in self.relays.items():
            log_dict[name] = "PASS" if item.passed else "FAIL"
        
        return log_dict
    
    def get_log_headers(self) -> List[str]:
        """
        Get headers for Excel logging in correct order.
        Note: Fixed headers (Date, Time, etc.) are added by ExcelLogger
        
        Returns:
            List of dynamic header names (peripherals, digital inputs, relays)
        """
        headers = []
        headers.extend(self.peripherals.keys())
        headers.extend(self.digital_inputs.keys())
        headers.extend(self.relays.keys())
        return headers
    
    # ========================================================================
    # UTILITY
    # ========================================================================
    
    def get_test_summary_string(self) -> str:
        """Get formatted summary of all test attempts"""
        if not self.test_history:
            return "No tests recorded"
        
        lines = ["=" * 50, "TEST SUMMARY", "=" * 50]
        
        for attempt in self.test_history:
            status = "✓ PASS" if attempt.overall_pass else "✗ FAIL"
            lines.append(f"\nAttempt {attempt.attempt_number}: {status}")
            lines.append(f"  Time: {attempt.timestamp.strftime('%H:%M:%S')}")
            lines.append(f"  Clock: {attempt.clock_frequency_hz} Hz ({'OK' if attempt.clock_pass else 'FAIL'})")
            lines.append(f"  Config: {attempt.config_state}")
            
            if not attempt.overall_pass:
                if attempt.peripherals_failed:
                    lines.append(f"  Peripherals Failed: {', '.join(attempt.peripherals_failed)}")
                if attempt.digital_inputs_failed:
                    lines.append(f"  Digital Inputs Failed: {', '.join(attempt.digital_inputs_failed)}")
                if attempt.relays_failed:
                    lines.append(f"  Relays Failed: {', '.join(attempt.relays_failed)}")
        
        lines.append("=" * 50)
        return "\n".join(lines)
