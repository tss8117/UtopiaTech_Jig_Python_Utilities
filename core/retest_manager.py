# ============================================================================
# JIG ONE v1.1 - Retest Manager
# ============================================================================
# Implements retest logic with uint32_t category masks per Protocol v1.1
# ============================================================================

from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

from config.constants import (
    TestMode,
    RetestStrategy,
    TestCategory,
    RetestMask,
)
from config.settings import (
    USER_MODE_MAX_RETRIES,
    MAX_DEVELOPER_RETRIES,
    DEFAULT_DEVELOPER_RETRIES,
    DEVELOPER_MODE_ENABLED,
)


@dataclass
class RetestAttempt:
    """Record of a single test/retest attempt"""
    attempt: int
    timestamp: datetime
    peripherals_failed: List[str] = field(default_factory=list)
    digital_inputs_failed: List[str] = field(default_factory=list)
    relays_failed: List[str] = field(default_factory=list)
    overall_pass: bool = False
    
    def __post_init__(self):
        self.overall_pass = (
            len(self.peripherals_failed) == 0 and
            len(self.digital_inputs_failed) == 0 and
            len(self.relays_failed) == 0
        )


class RetestManager:
    """
    Manages test retry logic for JIG ONE.
    
    Features:
    - User Mode: Automatic retries with FAILED_ONLY strategy
    - Developer Mode: Configurable retries and strategies
    - Protocol v1.1 compliant uint32_t retest masks
    """
    
    def __init__(self, developer_mode: bool = None):
        """
        Initialize RetestManager.
        
        Args:
            developer_mode: Override developer mode detection. If None, uses settings.
        """
        if developer_mode is None:
            developer_mode = DEVELOPER_MODE_ENABLED
            
        self.developer_mode = developer_mode
        self.current_mode = TestMode.DEVELOPER_MODE if developer_mode else TestMode.USER_MODE
        
        # Retry configuration
        if self.current_mode == TestMode.USER_MODE:
            self.max_retries = USER_MODE_MAX_RETRIES
            self.retest_strategy = RetestStrategy.FAILED_ONLY
        else:
            self.max_retries = DEFAULT_DEVELOPER_RETRIES
            self.retest_strategy = RetestStrategy.FAILED_ONLY
        
        # State tracking
        self.current_attempt = 0
        self.test_history: List[RetestAttempt] = []
        self.failed_categories: List[TestCategory] = []
        
        # Retest state
        self.is_retesting = False
        self.retest_in_progress = False
        self.specific_test_to_retry: Optional[TestCategory] = None
        
        # Callbacks
        self._on_retest_start: Optional[Callable] = None
        self._on_retest_complete: Optional[Callable] = None
    
    # ========================================================================
    # MODE CONFIGURATION
    # ========================================================================
    
    def set_mode(self, mode: TestMode):
        """Set test mode (USER or DEVELOPER)"""
        self.current_mode = mode
        if mode == TestMode.USER_MODE:
            self.max_retries = USER_MODE_MAX_RETRIES
            self.retest_strategy = RetestStrategy.FAILED_ONLY
    
    def set_developer_retries(self, count: int):
        """Set retry count in developer mode"""
        if self.current_mode == TestMode.DEVELOPER_MODE:
            self.max_retries = min(max(1, count), MAX_DEVELOPER_RETRIES)
    
    def set_retest_strategy(self, strategy: RetestStrategy):
        """Set retest strategy in developer mode"""
        if self.current_mode == TestMode.DEVELOPER_MODE:
            self.retest_strategy = strategy
    
    # ========================================================================
    # TEST LIFECYCLE
    # ========================================================================
    
    def reset_for_new_test(self):
        """Reset manager for a new test cycle"""
        self.current_attempt = 0
        self.test_history.clear()
        self.failed_categories.clear()
        self.is_retesting = False
        self.retest_in_progress = False
        self.specific_test_to_retry = None
    
    def record_test_result(
        self,
        peri_failed: List[str],
        dig_failed: List[str],
        relay_failed: List[str]
    ) -> bool:
        """
        Record test results from current attempt.
        
        Args:
            peri_failed: List of failed peripheral names
            dig_failed: List of failed digital input names
            relay_failed: List of failed relay names
            
        Returns:
            True if all tests passed, False otherwise
        """
        result = RetestAttempt(
            attempt=self.current_attempt,
            timestamp=datetime.now(),
            peripherals_failed=peri_failed.copy(),
            digital_inputs_failed=dig_failed.copy(),
            relays_failed=relay_failed.copy()
        )
        self.test_history.append(result)
        
        # Update failed categories
        self.failed_categories.clear()
        if peri_failed:
            self.failed_categories.append(TestCategory.PERIPHERALS)
        if dig_failed:
            self.failed_categories.append(TestCategory.DIGITAL_INPUTS)
        if relay_failed:
            self.failed_categories.append(TestCategory.RELAYS)
        
        return result.overall_pass
    
    # ========================================================================
    # RETRY DECISION LOGIC
    # ========================================================================
    
    def should_retry(self) -> bool:
        """
        Determine if a retry should be attempted.
        
        Returns:
            True if retry should be attempted, False otherwise
        """
        # No history means no test run yet
        if not self.test_history:
            print("No test history available, cannot determine retry")
            return False
        
        # Max retries reached
        if self.current_attempt >= self.max_retries:
            print(f"Max retries reached ({self.current_attempt}/{self.max_retries}), no more retries allowed")
            return False
        
        # Last test passed, no retry needed
        if self.test_history[-1].overall_pass:
            print("Last test passed, no retry needed")
            return False
        
        return True
    
    def get_tests_to_retry(self) -> List[TestCategory]:
        """
        Get list of test categories to retry based on strategy.
        
        Returns:
            List of TestCategory to retry
        """
        if self.retest_strategy == RetestStrategy.FULL_SEQUENCE:
            return [TestCategory.ALL]
        
        elif self.retest_strategy == RetestStrategy.FAILED_ONLY:
            return self.failed_categories.copy()
        
        elif self.retest_strategy == RetestStrategy.SPECIFIC_TEST:
            if self.specific_test_to_retry:
                return [self.specific_test_to_retry]
            return []
        
        return []
    
    def get_retest_mask(self) -> int:
        """
        Get uint32_t retest mask for protocol v1.1.
        
        Returns:
            uint32_t mask value for CMD_RETEST command
        """
        tests = self.get_tests_to_retry()
        
        if TestCategory.ALL in tests:
            return RetestMask.ALL
        
        mask = RetestMask.NONE
        
        if TestCategory.PERIPHERALS in tests:
            mask |= RetestMask.PERIPHERALS
        if TestCategory.DIGITAL_INPUTS in tests:
            mask |= RetestMask.DIG_INPUTS
        if TestCategory.RELAYS in tests:
            mask |= RetestMask.RELAYS
        if TestCategory.ADDITIONAL in tests:
            mask |= RetestMask.ADDITIONAL
        
        return mask
    
    # ========================================================================
    # RETRY EXECUTION
    # ========================================================================
    
    def start_retry(self):
        """Mark the start of a retry attempt"""
        self.current_attempt += 1
        self.is_retesting = True
        self.retest_in_progress = True
        
        if self._on_retest_start:
            self._on_retest_start(self.current_attempt, self.get_tests_to_retry())
    
    def end_retry(self):
        """Mark the end of a retry attempt"""
        self.retest_in_progress = False
        
        if self._on_retest_complete:
            last_result = self.test_history[-1] if self.test_history else None
            self._on_retest_complete(self.current_attempt, last_result)
    
    def set_specific_test(self, category: TestCategory):
        """Set specific test category for SPECIFIC_TEST strategy"""
        self.specific_test_to_retry = category
        self.retest_strategy = RetestStrategy.SPECIFIC_TEST
    
    # ========================================================================
    # CALLBACKS
    # ========================================================================
    
    def on_retest_start(self, callback: Callable):
        """Register callback for retest start"""
        self._on_retest_start = callback
    
    def on_retest_complete(self, callback: Callable):
        """Register callback for retest complete"""
        self._on_retest_complete = callback
    
    # ========================================================================
    # STATUS & REPORTING
    # ========================================================================
    
    def get_status_string(self) -> str:
        """Get human-readable status string"""
        mode_str = "USER" if self.current_mode == TestMode.USER_MODE else "DEV"
        strategy_str = self.retest_strategy.name.replace("_", " ")
        return f"Mode: {mode_str} | Attempt: {self.current_attempt}/{self.max_retries} | Strategy: {strategy_str}"
    
    def get_test_summary(self) -> str:
        """Get formatted summary of all test attempts"""
        if not self.test_history:
            return "No tests recorded"
        
        lines = ["=" * 40, "TEST SUMMARY", "=" * 40]
        
        for result in self.test_history:
            status = "âœ“ PASS" if result.overall_pass else "âœ— FAIL"
            lines.append(f"\nAttempt {result.attempt + 1}: {status}")
            lines.append(f"  Time: {result.timestamp.strftime('%H:%M:%S')}")
            
            if not result.overall_pass:
                if result.peripherals_failed:
                    lines.append(f"  Peripherals Failed: {', '.join(result.peripherals_failed)}")
                if result.digital_inputs_failed:
                    lines.append(f"  Digital Inputs Failed: {', '.join(result.digital_inputs_failed)}")
                if result.relays_failed:
                    lines.append(f"  Relays Failed: {', '.join(result.relays_failed)}")
        
        lines.append("=" * 40)
        return "\n".join(lines)
    
    def get_retry_info(self) -> Dict:
        """Get retry information as dictionary"""
        return {
            'mode': self.current_mode.name,
            'current_attempt': self.current_attempt,
            'max_retries': self.max_retries,
            'strategy': self.retest_strategy.name,
            'is_retesting': self.is_retesting,
            'failed_categories': [c.name for c in self.failed_categories],
            'attempts_remaining': max(0, self.max_retries - self.current_attempt)
        }
    
    @property
    def has_more_retries(self) -> bool:
        """Check if more retries are available"""
        return self.current_attempt < self.max_retries
    
    @property
    def last_result_passed(self) -> bool:
        """Check if last test result was a pass"""
        if not self.test_history:
            return False
        return self.test_history[-1].overall_pass


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def category_to_mask(category: TestCategory) -> int:
    """Convert TestCategory to retest mask value"""
    mapping = {
        TestCategory.PERIPHERALS: RetestMask.PERIPHERALS,
        TestCategory.DIGITAL_INPUTS: RetestMask.DIG_INPUTS,
        TestCategory.RELAYS: RetestMask.RELAYS,
        TestCategory.ADDITIONAL: RetestMask.ADDITIONAL,
        TestCategory.ALL: RetestMask.ALL,
    }
    return mapping.get(category, RetestMask.NONE)


def mask_to_categories(mask: int) -> List[TestCategory]:
    """Convert retest mask to list of TestCategory"""
    if mask == RetestMask.ALL:
        return [TestCategory.ALL]
    
    categories = []
    if mask & RetestMask.PERIPHERALS:
        categories.append(TestCategory.PERIPHERALS)
    if mask & RetestMask.DIG_INPUTS:
        categories.append(TestCategory.DIGITAL_INPUTS)
    if mask & RetestMask.RELAYS:
        categories.append(TestCategory.RELAYS)
    if mask & RetestMask.ADDITIONAL:
        categories.append(TestCategory.ADDITIONAL)
    
    return categories


def mask_to_string(mask: int) -> str:
    """Convert retest mask to human-readable string"""
    if mask == RetestMask.ALL:
        return "ALL"
    if mask == RetestMask.NONE:
        return "NONE"
    
    parts = []
    if mask & RetestMask.PERIPHERALS:
        parts.append("PERI")
    if mask & RetestMask.DIG_INPUTS:
        parts.append("DIG")
    if mask & RetestMask.RELAYS:
        parts.append("RELAY")
    if mask & RetestMask.ADDITIONAL:
        parts.append("ADD")
    
    return "+".join(parts) if parts else "NONE"
