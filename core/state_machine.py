# ============================================================================
# JIG ONE v1.2 - State Machine (with Programming Retry Logic)
# ============================================================================
# Manages the automated test sequence with retry capability for programming
# ============================================================================

from typing import Optional, Callable, Dict, Any
from threading import Thread, Event, Lock
from queue import Queue
from enum import Enum, auto
import time

from config.constants import (
    AppState,
    CommandID,
    DeviceAddress,
    FirmwareType,
    JigRelayID,
    RelayState,
    ErrorCode,
)
from config.settings import (
    INTER_FRAME_DELAY,
    DUT_RESET_PULSE,
)
from core.protocol import ProtocolHandler, RS485Frame
from core.serial_handler import SerialHandler
from core.retest_manager import RetestManager


class StateMachineEvent(Enum):
    """Events that trigger state transitions"""
    START_BUTTON_PRESSED = auto()
    BOOTLOADER_SUCCESS = auto()
    BOOTLOADER_FAILED = auto()
    TEST_CODE_SUCCESS = auto()
    TEST_CODE_FAILED = auto()
    TEST_RESULTS_RECEIVED = auto()
    TEST_PASSED = auto()
    TEST_FAILED = auto()
    RETRY_REQUESTED = auto()
    CONFIG_SUCCESS = auto()
    CONFIG_FAILED = auto()
    FINAL_FW_SUCCESS = auto()
    FINAL_FW_FAILED = auto()
    COMM_FAILED = auto()
    ABORT = auto()
    RESET = auto()


class TestStateMachine:
    """
    Manages the automated test sequence.
    
    State Flow:
    IDLE → BOOTLOADER → TEST_FW → TESTING → CONFIG → FINAL_FW → IDLE
                ↓              ↓                ↓
           (RETRY if fail) (RETRY if fail) (RETRY if fail)
    
    NEW in v1.2:
    - Programming retry logic (max 2 attempts per stage)
    - Test retry logic (via RetestManager)
    """
    
    def __init__(
        self,
        serial_handler: SerialHandler,
        retest_manager: RetestManager
    ):
        self.serial = serial_handler
        self.retest_manager = retest_manager
        
        # Current state
        self._state = AppState.AUTO_PROGRAM_NULL
        self._bootloader_state = AppState.BOOTLOADER_NULL
        self._test_fw_state = AppState.TEST_FIRM_NULL
        self._testing_state = AppState.TESTING_PROCESS_NULL
        self._config_state = AppState.SETTING_CONF_NULL
        self._final_fw_state = AppState.FINAL_FIRM_NULL
        
        # ====================================================================
        # NEW: Programming retry tracking
        # ====================================================================
        self.max_programming_retries = 2  # 1 initial + 1 retry
        self.bootloader_attempt = 0
        self.test_fw_attempt = 0
        self.final_fw_attempt = 0
        
        # State machine control
        self._lock = Lock()
        self._stop_event = Event()
        self._sm_thread: Optional[Thread] = None
        self._event_queue: Queue[StateMachineEvent] = Queue()
        
        # Device configuration
        self.serial_no: str = ""
        self.mac_id: str = ""
        
        # Firmware paths (set externally)
        self.bootloader_path: str = ""
        self.test_code_path: str = ""
        self.final_fw_path: str = ""
        
        # Callbacks
        self._callbacks: Dict[str, Callable] = {}
        
        # Programming function (set externally)
        self._program_firmware: Optional[Callable[[str], None]] = None
    
    # ========================================================================
    # STATE PROPERTIES
    # ========================================================================
    
    @property
    def state(self) -> AppState:
        with self._lock:
            return self._state
    
    @state.setter
    def state(self, new_state: AppState):
        with self._lock:
            old_state = self._state
            self._state = new_state
        
        # Notify state change
        self._notify('on_state_change', old_state, new_state)
    
    @property
    def is_running(self) -> bool:
        return self._state != AppState.AUTO_PROGRAM_NULL
    
    @property
    def is_idle(self) -> bool:
        return self._state == AppState.AUTO_PROGRAM_NULL
    
    # ========================================================================
    # STATE MACHINE CONTROL
    # ========================================================================
    
    def start(self) -> bool:
        """
        Start the test state machine.
        
        Returns:
            True if started successfully
        """
        # Validate prerequisites
        if not self._validate_prerequisites():
            return False
        
        # Reset states
        self._reset_states()
        self.retest_manager.reset_for_new_test()
        
        # ====================================================================
        # NEW: Reset programming attempt counters
        # ====================================================================
        self.bootloader_attempt = 0
        self.test_fw_attempt = 0
        self.final_fw_attempt = 0
        
        # Start state machine thread
        self._stop_event.clear()
        self._sm_thread = Thread(target=self._run_state_machine, daemon=True)
        self._sm_thread.start()
        
        self.state = AppState.AUTO_PROGRAM_START
        self._notify('on_test_start')
        
        return True
    
    def stop(self):
        """Stop the state machine"""
        self._stop_event.set()
        self._event_queue.put(StateMachineEvent.ABORT)
        
        if self._sm_thread and self._sm_thread.is_alive():
            self._sm_thread.join(timeout=5.0)
        
        self._reset_states()
        self._notify('on_test_stop')
    
    def reset(self):
        """Reset state machine to initial state"""
        self.stop()
        self._reset_states()
        self._notify('on_reset')
    
    def post_event(self, event: StateMachineEvent):
        """Post an event to the state machine"""
        self._event_queue.put(event)
    
    # ========================================================================
    # STATE MACHINE LOGIC (WITH PROGRAMMING RETRY)
    # ========================================================================
    
    def _run_state_machine(self):
        """Main state machine loop with programming retry logic"""
        print("[SM] State machine started")
        
        while not self._stop_event.is_set():
            try:
                current = self.state
                
                # ============================================================
                # AUTO_PROGRAM_START: Begin with bootloader
                # ============================================================
                if current == AppState.AUTO_PROGRAM_START:
                    self.bootloader_attempt = 0  # Reset counter
                    self._do_program_bootloader()
                
                # ============================================================
                # AUTO_PROGRAM_BOOTLOADER: Wait for bootloader result
                # ============================================================
                elif current == AppState.AUTO_PROGRAM_BOOTLOADER:
                    if self._bootloader_state == AppState.BOOTLOADER_PROGRAMMED_DUT_RST:
                        # Success - move to test firmware
                        self.test_fw_attempt = 0  # Reset counter
                        self._do_program_test_firmware()
                        
                    elif self._bootloader_state == AppState.BOOTLOADER_PROGRAMMED_FAIL:
                        # Failed - check if retry available
                        self.bootloader_attempt += 1
                        
                        if self.bootloader_attempt < self.max_programming_retries:
                            # RETRY BOOTLOADER
                            self._notify('on_log', 
                                f"Bootloader programming failed, retry attempt {self.bootloader_attempt}/{self.max_programming_retries}", "WARNING")
                            
                            # Reset state for retry
                            self._bootloader_state = AppState.BOOTLOADER_NULL
                            time.sleep(4)  # Allow ST-Link USB to re-enumerate before retry
                            
                            # Retry programming
                            self._do_program_bootloader()
                        else:
                            # MAX RETRIES REACHED - ABORT
                            self._notify('on_log', 
                                f"Bootloader programming failed after {self.max_programming_retries} attempts", "ERROR")
                            # Send final PROG_ACK (FAIL)
                            frame = ProtocolHandler.build_prog_ack(FirmwareType.BOOTLOADER, False)
                            self.serial.write_frame(frame)
                            self._handle_failure("Bootloader programming failed after max retries")
                            break
                
                # ============================================================
                # AUTO_PROGRAM_TEST_FIRM: Wait for test firmware result
                # ============================================================
                elif current == AppState.AUTO_PROGRAM_TEST_FIRM:
                    if self._test_fw_state == AppState.TEST_FIRM_PROGRAMMED_PASS:
                        # Success - move to testing
                        self.state = AppState.AUTO_TESTING_PROCESS
                        
                    elif self._test_fw_state == AppState.TEST_FIRM_PROGRAMMED_FAIL:
                        # Failed - check if retry available
                        self.test_fw_attempt += 1
                        
                        if self.test_fw_attempt < self.max_programming_retries:
                            # RETRY TEST FIRMWARE
                            self._notify('on_log', 
                                f"Test firmware programming failed, retry attempt {self.test_fw_attempt}/{self.max_programming_retries}", "WARNING")
                            
                            # Reset state for retry
                            self._test_fw_state = AppState.TEST_FIRM_NULL
                            time.sleep(4)  # Allow ST-Link USB to re-enumerate before retry
                            
                            # Retry programming
                            self._do_program_test_firmware()
                        else:
                            # MAX RETRIES REACHED - ABORT
                            self._notify('on_log', 
                                f"Test firmware programming failed after {self.max_programming_retries} attempts", "ERROR")
                            
                            # Send final PROG_ACK (FAIL)
                            frame = ProtocolHandler.build_prog_ack(FirmwareType.TEST_CODE, False)
                            self.serial.write_frame(frame)

                            self._handle_failure("Test firmware programming failed after max retries")
                            break
                
                # ============================================================
                # AUTO_TESTING_PROCESS: Wait for test results
                # ============================================================
                elif current == AppState.AUTO_TESTING_PROCESS:
                    if self._testing_state == AppState.TESTING_PROCESS_PASS:
                        self.state = AppState.AUTO_SETTING_CONF_PROCESS
                    elif self._testing_state == AppState.TESTING_PROCESS_FAIL:
                        self._handle_failure("Testing failed after max retries")
                        break
                
                # ============================================================
                # AUTO_RETESTING: Wait for retest results
                # ============================================================
                elif current == AppState.AUTO_RETESTING:
                    if self._testing_state == AppState.TESTING_PROCESS_PASS:
                        self.state = AppState.AUTO_SETTING_CONF_PROCESS
                    elif self._testing_state == AppState.TESTING_PROCESS_FAIL:
                        self._handle_failure("Testing failed after max retries")
                        break
                
                # ============================================================
                # AUTO_SETTING_CONF_PROCESS: Wait for config result
                # ============================================================
                elif current == AppState.AUTO_SETTING_CONF_PROCESS:
                    if self._config_state == AppState.SETTING_CONF_PASS:
                        self.final_fw_attempt = 0  # Reset counter
                        self._do_program_final_firmware()
                    elif self._config_state == AppState.SETTING_CONF_FAIL:
                        self._handle_failure("Configuration setting failed")
                        break
                
                # ============================================================
                # AUTO_PROGRAM_FINAL_FIRM: Wait for final firmware result
                # ============================================================
                elif current == AppState.AUTO_PROGRAM_FINAL_FIRM:
                    if self._final_fw_state == AppState.FINAL_FIRM_PROGRAMMED_PASS:
                        # Success - complete test
                        self._handle_success()
                        break
                        
                    elif self._final_fw_state == AppState.FINAL_FIRM_PROGRAMMED_FAIL:
                        # Failed - check if retry available
                        self.final_fw_attempt += 1
                        
                        if self.final_fw_attempt < self.max_programming_retries:
                            # RETRY FINAL FIRMWARE
                            self._notify('on_log', 
                                f"Final firmware programming failed, retry attempt {self.final_fw_attempt}/{self.max_programming_retries}", "WARNING")
                            
                            # Reset state for retry
                            self._final_fw_state = AppState.FINAL_FIRM_NULL
                            time.sleep(4)  # Allow ST-Link USB to re-enumerate before retry
                            
                            # Retry programming
                            self._do_program_final_firmware()
                        else:
                            # MAX RETRIES REACHED - ABORT
                            self._notify('on_log', 
                                f"Final firmware programming failed after {self.max_programming_retries} attempts", "ERROR")
                            
                            # Send final PROG_ACK (FAIL)
                            frame = ProtocolHandler.build_prog_ack(FirmwareType.FINAL, False)
                            self.serial.write_frame(frame)

                            self._handle_failure("Final firmware programming failed after max retries")
                            break
                
                # ============================================================
                # AUTO_NO_COMMUNICATION: Communication error
                # ============================================================
                elif current == AppState.AUTO_NO_COMMUNICATION:
                    self._handle_failure("Communication failed")
                    break
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"[SM] Error: {e}")
                self._handle_failure(f"State machine error: {e}")
                break
        
        print("[SM] State machine ended")
    
    # ========================================================================
    # STATE ACTIONS
    # ========================================================================
    
    def _do_program_bootloader(self):
        """Execute bootloader programming"""
        # self._notify('on_log', "Programming bootloader...", "INFO")
        
        # Send start programming ACK to JIG
        frame = ProtocolHandler.build_start_prog_ack(0x01)
        time.sleep(INTER_FRAME_DELAY)
        self.serial.write_frame(frame)
        
        self.state = AppState.AUTO_PROGRAM_BOOTLOADER
        
        # Trigger external programming (OpenOCD)
        if self._program_firmware:
            self._program_firmware("BOOTLOADER")
    
    def _do_program_test_firmware(self):
        """Execute test firmware programming"""
        # self._notify('on_log', "Programming test firmware...", "INFO")
        self.state = AppState.AUTO_PROGRAM_TEST_FIRM
        
        if self._program_firmware:
            self._program_firmware("TEST")
    
    def _do_program_final_firmware(self):
        """Execute final firmware programming"""
        self._notify('on_log', "Programming final firmware...", "INFO")
        self.state = AppState.AUTO_PROGRAM_FINAL_FIRM
        
        if self._program_firmware:
            self._program_firmware("FINAL")
    
    def _do_dut_reset(self):
        """Send DUT reset pulse via JIG relay"""
        self._notify('on_log', "Resetting DUT...", "INFO")
        
        # Turn ON reset relay
        frame_on = ProtocolHandler.build_jig_relay_control(
            JigRelayID.RESET, RelayState.ON
        )
        # self.serial.write_frame(frame_on)
        
        time.sleep(DUT_RESET_PULSE)
        
        # Turn OFF reset relay
        frame_off = ProtocolHandler.build_jig_relay_control(
            JigRelayID.RESET, RelayState.OFF
        )
        # self.serial.write_frame(frame_off)
    
    def _do_send_config(self):
        """Send configuration to DUT"""
        self._notify('on_log', "Sending configuration to DUT...", "INFO")
        
        try:
            serial_no_int = int(self.serial_no)
            mac_id_int = int(self.mac_id, 16)
            rtc_timestamp = int(time.time())
            
            frame = ProtocolHandler.build_set_config(
                serial_no_int, mac_id_int, (rtc_timestamp+19800)
            )
            time.sleep(2)
            self.serial.write_frame(frame)
            
            self._notify('on_log', 
                f"Config sent: Serial={self.serial_no}, RTC={rtc_timestamp}", "INFO")
            
        except Exception as e:
            self._notify('on_log', f"Failed to send config: {e}", "ERROR")
            self._config_state = AppState.SETTING_CONF_FAIL
    
    def _do_initiate_retest(self):
        """Initiate retest sequence"""
        # REMOVED: self.retest_manager.start_retry() - already called in main_window
        
        mask = self.retest_manager.get_retest_mask()
        categories = self.retest_manager.get_tests_to_retry()
        
        self._notify('on_log', 
            f"Initiating retest (attempt {self.retest_manager.current_attempt + 1}): "
            f"{[c.name for c in categories]}", "INFO")
        
        frame = ProtocolHandler.build_retest_command(mask)
        time.sleep(INTER_FRAME_DELAY)
        self.serial.write_frame(frame)
        
        self.state = AppState.AUTO_RETESTING

    # def _do_initiate_retest(self):
    #     """Initiate retest sequence"""
    #     self.retest_manager.start_retry()
        
    #     mask = self.retest_manager.get_retest_mask()
    #     categories = self.retest_manager.get_tests_to_retry()
        
    #     self._notify('on_log', "INFO", 
    #         f"Initiating retest (attempt {self.retest_manager.current_attempt + 1}): "
    #         f"{[c.name for c in categories]}")
        
    #     frame = ProtocolHandler.build_retest_command(mask)
    #     time.sleep(INTER_FRAME_DELAY)
    #     self.serial.write_frame(frame)
        
    #     self.state = AppState.AUTO_RETESTING
    
    # ========================================================================
    # RESULT HANDLERS
    # ========================================================================
    
    def _handle_success(self):
        """Handle successful test completion"""
        self._notify('on_log', "TEST COMPLETED SUCCESSFULLY", "SUCCESS")

        # Turn on green LED
        frame = ProtocolHandler.build_jig_relay_control(
            JigRelayID.GREEN_LED, RelayState.ON
        )
        self.serial.write_frame(frame)
        
        self._reset_states()
        
        self._notify('on_test_complete', True)
    
    def _handle_failure(self, reason: str):
        """Handle test failure"""
        # self._notify('on_log', f"Test failed: {reason}", "ERROR")
        
        # Turn on red LED
        frame = ProtocolHandler.build_jig_relay_control(
            JigRelayID.RED_LED, RelayState.ON
        )
        self.serial.write_frame(frame)
        
        self._reset_states()
        self._notify('on_test_complete', False)
    
    # ========================================================================
    # EXTERNAL UPDATES (called from frame handler)
    # ========================================================================
    
    def on_bootloader_result(self, success: bool):
        """Update bootloader programming result"""
        if success:
            self._bootloader_state = AppState.BOOTLOADER_PROGRAMMED_PASS
            # Send PROG_ACK
            frame = ProtocolHandler.build_prog_ack(FirmwareType.BOOTLOADER, True)
            self.serial.write_frame(frame)
            # Reset DUT
            # self._do_dut_reset()
            self._bootloader_state = AppState.BOOTLOADER_PROGRAMMED_DUT_RST
        else:
            self._bootloader_state = AppState.BOOTLOADER_PROGRAMMED_FAIL
            # frame = ProtocolHandler.build_prog_ack(FirmwareType.BOOTLOADER, False)
            # self.serial.write_frame(frame)
    
    def on_test_firmware_result(self, success: bool):
        """Update test firmware programming result"""
        if success:
            self._test_fw_state = AppState.TEST_FIRM_PROGRAMMED_PASS
            frame = ProtocolHandler.build_prog_ack(FirmwareType.TEST_CODE, True)
            self.serial.write_frame(frame)
            # self._do_dut_reset()
        else:
            self._test_fw_state = AppState.TEST_FIRM_PROGRAMMED_FAIL
            # frame = ProtocolHandler.build_prog_ack(FirmwareType.TEST_CODE, False)
            # self.serial.write_frame(frame)

    def on_testing_complete(self, all_passed: bool):
        """Update testing result"""
        if all_passed:
            self._testing_state = AppState.TESTING_PROCESS_PASS
            self._do_send_config()
        else:
            # FIXED: Retest logic already handled in main_window
            # State machine should only check final result after all retries
            # The retest_manager.should_retry() is called in main_window._handle_test_complete()
            # If we get here with all_passed=False, it means retries exhausted
            self._testing_state = AppState.TESTING_PROCESS_FAIL

    # def on_testing_complete(self, all_passed: bool):
    #     """Update testing result"""
    #     if all_passed:
    #         self._testing_state = AppState.TESTING_PROCESS_PASS
    #         self._do_send_config()
    #     else:
    #         # Check if retry is needed
    #         if self.retest_manager.should_retry():
    #             self._do_initiate_retest()
    #         else:
    #             self._testing_state = AppState.TESTING_PROCESS_FAIL
    #             self.retest_manager.end_retry()
    
    def on_config_result(self, success: bool):
        """Update configuration result"""
        if success:
            self._config_state = AppState.SETTING_CONF_PASS
        else:
            self._config_state = AppState.SETTING_CONF_FAIL
    
    def on_final_firmware_result(self, success: bool):
        """Update final firmware programming result"""
        if success:
            self._final_fw_state = AppState.FINAL_FIRM_PROGRAMMED_PASS
            frame = ProtocolHandler.build_prog_ack(FirmwareType.FINAL, True)
            self.serial.write_frame(frame)
            # Also send PROG_FINAL ACK
            frame2 = ProtocolHandler.build_prog_final_ack(0x02)
            self.serial.write_frame(frame2)
        else:
            self._final_fw_state = AppState.FINAL_FIRM_PROGRAMMED_FAIL
            # frame = ProtocolHandler.build_prog_ack(FirmwareType.FINAL, False)
            # self.serial.write_frame(frame)
    
    def on_comm_failed(self):
        """Handle communication failure"""
        self.state = AppState.AUTO_NO_COMMUNICATION
    
    # ========================================================================
    # CALLBACKS
    # ========================================================================
    
    def register_callback(self, name: str, callback: Callable):
        """Register a callback"""
        self._callbacks[name] = callback
    
    def _notify(self, name: str, *args):
        """Notify callback if registered"""
        if name in self._callbacks:
            try:
                self._callbacks[name](*args)
            except Exception as e:
                print(f"[SM] Callback error ({name}): {e}")
    
    def set_program_firmware_callback(self, callback: Callable[[str], None]):
        """Set the firmware programming callback"""
        self._program_firmware = callback
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    def _validate_prerequisites(self) -> bool:
        """Validate prerequisites for starting test"""
        errors = []
        
        if not self.serial.is_connected:
            errors.append("Serial port not connected")
        
        if not self.bootloader_path:
            errors.append("Bootloader firmware not selected")
        
        if not self.test_code_path:
            errors.append("Test firmware not selected")
        
        if not self.final_fw_path:
            errors.append("Final firmware not selected")
        
        if not self.serial_no:
            errors.append("Serial number not set")
        
        if not self.mac_id:
            errors.append("MAC ID not set")
        
        if errors:
            for error in errors:
                self._notify('on_log', error, "ERROR")
            return False
        
        return True
    
    def _reset_states(self):
        """Reset all internal states"""
        with self._lock:
            self._state = AppState.AUTO_PROGRAM_NULL
            self._bootloader_state = AppState.BOOTLOADER_NULL
            self._test_fw_state = AppState.TEST_FIRM_NULL
            self._testing_state = AppState.TESTING_PROCESS_NULL
            self._config_state = AppState.SETTING_CONF_NULL
            self._final_fw_state = AppState.FINAL_FIRM_NULL
