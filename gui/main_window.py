# ============================================================================
# JIG ONE v1.2 - Main Window
# ============================================================================
# Updated for Protocol v1.2 with TLV format and combined results frame
# ============================================================================

import customtkinter as ctk
from typing import Optional
import time


from config.constants import ProgStatus

from config import (
    JIG_FORMAT_VERSION,
    VERSION,
    DEVELOPER_MODE_ENABLED,
    TlvTag,
    DeviceAddress,
    TestCategory,
    RetestStrategy,
    DEV_DEFAULT_SERIAL_NO,
    DEV_DEFAULT_MAC_ID,
    USER_MODE_MAX_RETRIES,
)
from config.settings import (
    get_window_dimensions,
    MIN_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
    SCREEN_COVERAGE_RATIO,
)
from models import ProductConfig, TestResultsManager
from core import (
    serial_handler,
    ProtocolHandler,
    RetestManager,
    TestStateMachine,
    RS485Frame,
    SerialHandler
)
from core.tlv_parser import (
    TlvParser,
    configure_tlv_parser,
    TlvParseError,
    UnknownTagError,
    BitmapValidationError,
)
from services import firmware_programmer, excel_logger, qr_scanner
from utils import text_logger, MessageQueue
from gui.widgets import LogTextbox
from gui.frames import SerialFrame, ConfigFrame, ResultsFrame, DeveloperFrame


class MainWindow:
    """
    Main application window for JIG ONE Testing Utility v1.2.
    
    Key Changes from v1.1:
    - TLV format for all protocol messages
    - Combined results frame (single frame with all test results)
    - Dynamic TLV parser from JSON config
    - Monthly/daily Excel logging structure
    """
    
    def __init__(self):
        # Initialize components
        self.product_config = ProductConfig()
        self.results_manager = TestResultsManager(self.product_config)
        self.retest_manager = RetestManager(developer_mode=DEVELOPER_MODE_ENABLED)
        self.state_machine = TestStateMachine(serial_handler, self.retest_manager)
        self.serial = serial_handler
        # Configure TLV parser from product config
        self.tlv_parser = configure_tlv_parser(self.product_config)
        
        # Message queue for cross-thread communication
        self.message_queue = MessageQueue()
        self._setup_message_handlers()
        
        # Setup callbacks
        self._setup_callbacks()
        
        # Initialize GUI
        self._setup_window()
        self._build_ui()
        
        # Configure Excel logger with product info and headers
        excel_logger.set_product_name(self.product_config.product_name)
        excel_logger.set_headers(self.results_manager.get_log_headers())
        
        # Startup logging
        self._log_startup()
        
        # Bind keyboard for QR scanner
        self.root.bind('<Key>', self._on_keypress)
        
        # Bind resize events
        self.root.bind('<Configure>', self._on_resize)

        self.serial_frame.auto_connect()
        
        # Start message queue processing
        self._check_queue()
    
    def _setup_window(self):
        """Setup the main window with dynamic sizing"""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        
        # Build window title
        title = f"{JIG_FORMAT_VERSION} TESTING UTILITY v{VERSION}"
        title += f" - {self.product_config.product_name}"
        if DEVELOPER_MODE_ENABLED:
            title += " [DEVELOPER MODE]"
        
        self.root.title(title)
        
        # Get dynamic window dimensions (90% of screen)
        win_w, win_h, x_offset, y_offset = get_window_dimensions(self.root)
        
        # Store dimensions
        self.window_width = win_w
        self.window_height = win_h
        
        # Set window geometry
        self.root.geometry(f"{win_w}x{win_h}+{x_offset}+{y_offset}")
        
        # Set minimum window size
        self.root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        
        # Allow window resizing
        self.root.resizable(True, True)
        
        # Padding constants (relative)
        self.cpadx = 0.005
        self.cpady = 0.01
        
        print(f"[GUI] Window: {win_w}x{win_h} at ({x_offset},{y_offset})")
    
    def _on_resize(self, event):
        """Handle window resize events"""
        # Only handle root window resize
        if event.widget == self.root:
            new_width = event.width
            new_height = event.height
            
            # Update stored dimensions if significant change
            if abs(new_width - self.window_width) > 10 or abs(new_height - self.window_height) > 10:
                self.window_width = new_width
                self.window_height = new_height
    
    def toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode"""
        is_fullscreen = self.root.attributes('-fullscreen')
        self.root.attributes('-fullscreen', not is_fullscreen)
        return "break"
    
    def exit_fullscreen(self, event=None):
        """Exit fullscreen mode"""
        self.root.attributes('-fullscreen', False)
        return "break"
    
    def _build_ui(self):
        """Build the main UI"""
        # Define layout proportions
        left_width = 0.52  # Slightly larger for config content
        right_width = 0.47
        
        # Serial Frame - top left
        self.serial_frame = SerialFrame(
            self.root,
            serial_handler=serial_handler,
            on_log=self._log_message
        )
        self.serial_frame.place(
            relx=self.cpadx,
            rely=self.cpady,
            relheight=0.06,
            relwidth=(left_width - self.cpadx)
        )
        
        # Config Frame - below serial
        self.config_frame = ConfigFrame(
            self.root,
            product_config=self.product_config,
            programmer=firmware_programmer,
            on_log=self._log_message,
            on_program=self._on_program_firmware,
            on_reset=self._user_reset
        )
        self.config_frame.place(
            relx=self.cpadx,
            rely=((2 * self.cpady) + 0.06),
            relheight=0.25,
            relwidth=(left_width - self.cpadx)
        )
        
        # Logs Frame - top right, adjust height based on developer mode
        logs_frame_height = 0.20 if DEVELOPER_MODE_ENABLED else 0.32
        
        logs_frame = ctk.CTkFrame(self.root)
        logs_frame.place(
            relx=left_width,
            rely=self.cpady,
            relheight=logs_frame_height,
            relwidth=(right_width - self.cpadx)
        )
        
        self.logs_textbox = LogTextbox(logs_frame)
        self.logs_textbox.place(relx=0.01, rely=0.02, relheight=0.96, relwidth=0.98)
        
        # Developer Frame (if enabled) - below logs
        if DEVELOPER_MODE_ENABLED:
            # NEW
            self.developer_frame = DeveloperFrame(
                self.root,
                retest_manager=self.retest_manager,
                on_load_defaults=self._load_dev_defaults,
                on_clear_ids=self._clear_dev_ids,
                on_reset=self._reset_utility,
                on_show_summary=self._show_test_summary,
                on_log=self._log_message
            )
            self.developer_frame.place(
                relx=left_width,
                rely=((2 * self.cpady) + logs_frame_height),
                relheight=0.11,
                relwidth=(right_width - self.cpadx)
            )
            
            # Load defaults
            self._load_dev_defaults()
        
        # Results Frame - bottom, full width
        results_top = (3 * self.cpady) + 0.32
        self.results_frame = ResultsFrame(
            self.root,
            product_config=self.product_config,
            results_manager=self.results_manager
        )
        self.results_frame.place(
            relx=self.cpadx,
            rely=results_top,
            relheight=(1.0 - results_top - self.cpady),
            relwidth=(1 - (2 * self.cpadx))
        )
    
    def _setup_callbacks(self):
        """Setup component callbacks"""
        # Serial frame received callback
        serial_handler.on_frame_received(self._on_frame_received)
        
        # Programmer callbacks
        firmware_programmer.on_success(self._on_programming_success)
        firmware_programmer.on_failure(self._on_programming_failure)
        
        # QR Scanner callbacks
        qr_scanner.on_serial_scanned(self._on_serial_scanned)
        qr_scanner.on_mac_scanned(self._on_mac_scanned)
        # qr_scanner.on_duplicate_serial(self._on_duplicate_serial)
        qr_scanner.set_serial_validator(lambda s: excel_logger.get_serial_state(s))
        
        # State machine callbacks
        self.state_machine.register_callback('on_log', self._log_message)
        self.state_machine.register_callback('on_test_complete', self._on_test_complete)
        self.state_machine.set_program_firmware_callback(self._on_program_firmware)
    
    def _setup_message_handlers(self):
        """Setup message queue handlers"""
        self.message_queue.register_handler('DUT_RST', self._handle_dut_reset)
        self.message_queue.register_handler('UPDATE_GUI', self._handle_gui_update)
        self.message_queue.register_handler('LOG', self._handle_log_message)
        self.message_queue.register_handler('TEST_COMPLETE', self._handle_test_complete_safe)
        self.message_queue.register_handler('COMM_FAILED', self._handle_comm_failed_safe)
        self.message_queue.register_handler('START_TEST', self._handle_start_test_safe)
        self.message_queue.register_handler('PROG_SUCCESS', self._handle_prog_success_safe)
        self.message_queue.register_handler('PROG_FAILURE', self._handle_prog_failure_safe)
        
    # =========================================================================
    # FRAME PARSING (Protocol v1.2 - TLV Format)
    # =========================================================================
    
    def _on_frame_received(self, frame: RS485Frame):
        """Handle received RS485 frame"""
        # Only process frames addressed to RASPi
        if frame.to_addr != DeviceAddress.RASPI:
            return
        
        # Process based on source
        if frame.from_addr == DeviceAddress.JIG_BOARD:
            self._handle_jig_frame(frame)
        elif frame.from_addr == DeviceAddress.DUT:
            self._handle_dut_frame(frame)
    
    def _handle_jig_frame(self, frame: RS485Frame):
        """
        Handle frame from JIG Board (Protocol v1.2 - TLV format).
        
        Key change: Combined results frame detected by first tag being PERIPHERALS
        and frame length >= 20 bytes.
        """
        first_tag = frame.first_tag
        tlv_data = frame.tlv_data
        
        # Check for combined results frame (v1.2)
        if ProtocolHandler.is_combined_results_frame(frame):
            self._handle_combined_results(tlv_data)
            return
        
        # Handle other TLV-based messages
        if first_tag == TlvTag.START_PROG:
            # Button press from JIG
            status = ProtocolHandler.parse_start_prog(tlv_data)
            if status == 0x00:  # Ready (button pressed)
                # self._start_test_sequence()
                self.message_queue.put('START_TEST', None)
        
        elif first_tag == TlvTag.ACK_STATUS:
            # Retest ACK
            ack = ProtocolHandler.parse_retest_ack(tlv_data)
            if ack:
                self._log_message("JIG acknowledged retest", "INFO")
            else:
                self._log_message("JIG rejected retest", "ERROR")
        
        elif first_tag == TlvTag.ERROR_CODE:
            # Communication failed
            error_code = ProtocolHandler.parse_error_code(tlv_data)
            self._log_message(f"Communication Failed (error: {error_code})", "ERROR")
            # self.state_machine.on_comm_failed()
            self.message_queue.put('COMM_FAILED', None)

    def _handle_combined_results(self, tlv_data: bytes):
        """
        Handle combined test results frame (Protocol v1.2).
        
        Single frame contains all test results:
        - Peripheral bitmap (2 bytes)
        - Clock frequency (4 bytes)
        - Digital input bitmap (8 bytes)
        - Relay bitmap (2 bytes)
        
        Frame end (0xD9) indicates results are complete - no separate marker needed.
        """
        try:
            # Parse all TLVs in the combined frame
            parsed = self.tlv_parser.parse_combined_results(tlv_data)
            
            # Apply parsed results to test items
            self.results_manager.apply_parsed_results(parsed)
            
            # Log the results
            self._log_message(
                f"Results received: Clock={parsed.clock_frequency_hz}Hz, "
                f"Peri=0x{parsed.peripheral_bitmap:04X}, "
                f"Dig=0x{parsed.digital_input_bitmap:016X}, "
                f"Relay=0x{parsed.relay_bitmap:04X}",
                "INFO"
            )
            
            # Log to text logger
            text_logger.log_section("TEST RESULTS (Combined Frame)")
            text_logger.log("INFO", f"Clock Frequency: {parsed.clock_frequency_hz} Hz")
            
            for name, passed in parsed.peripheral_results.items():
                text_logger.log_test_result(name, passed)
            
            for name, passed in parsed.digital_input_results.items():
                text_logger.log_test_result(name, passed)
            
            for name, passed in parsed.relay_results.items():
                text_logger.log_test_result(name, passed)
            
            # Update GUI
            self.message_queue.put('UPDATE_GUI', None)
            
            # Handle test completion (frame end = results complete in v1.2)
            # self._handle_test_complete()
            self.message_queue.put('TEST_COMPLETE', parsed)

        except UnknownTagError as e:
            self._log_message(f"Unknown TLV tag received: 0x{e.tag:02X}", "ERROR")
            # self.state_machine.on_comm_failed()
            self.message_queue.put('COMM_FAILED', None) 
            
        except BitmapValidationError as e:
            self._log_message(f"Bitmap validation failed: {e}", "ERROR")
            # Continue processing despite validation error (log warning, don't abort)
            
        except TlvParseError as e:
            self._log_message(f"TLV parse error: {e}", "ERROR")
            # self.state_machine.on_comm_failed()
            self.message_queue.put('COMM_FAILED', None) 
    
    def _handle_dut_frame(self, frame: RS485Frame):
        """Handle frame from DUT (Protocol v1.2 - TLV format)"""
        first_tag = frame.first_tag
        tlv_data = frame.tlv_data
        
        # SET_CONFIG echo (verification) - now uses TLV sub-fields
        if first_tag == TlvTag.SERIAL_NO:
            serial_no, mac_id, rtc = ProtocolHandler.parse_config_echo(tlv_data)
            
            expected_serial = int(self.config_frame.serial_no)
            expected_mac = int(self.config_frame.mac_id, 16)
            formatted_rtc = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(rtc))
            
            if serial_no == expected_serial and mac_id == expected_mac:
                self._log_message(f"Config verified. RTC set to: {formatted_rtc}", "SUCCESS")
                self.results_manager.set_config_state("SET")
                self.state_machine.on_config_result(True)
                
                # Log to Excel with current state
                log_dict = self.results_manager.to_log_dict(
                    self.config_frame.serial_no,
                    self.config_frame.mac_id,
                )
                excel_logger.log_result(log_dict)
            else:
                self._log_message(
                    f"Config verification failed: got Serial={serial_no}, MAC={mac_id:012X}",
                    "ERROR"
                )
                self.state_machine.on_config_result(False)
    
    # =========================================================================
    # TEST SEQUENCE
    # =========================================================================
    
    def _start_test_sequence(self):
        """Start the automated test sequence"""
        # Validate prerequisites
        if not self.config_frame.has_all_firmware():
            frame = ProtocolHandler.build_prog_status(ProgStatus.NO_FILES.value)
            self._log_message("Firmware files not selected", "ERROR")
            self.serial.write_frame(frame)
            return
        
        if not self.config_frame.has_device_info():
            frame = ProtocolHandler.build_prog_status(ProgStatus.NO_SCAN.value)
            self._log_message("Serial No. / MAC ID not set", "ERROR")
            self.serial.write_frame(frame)            
            return
        self._log_message("=" * 35, "INFO")
        self._log_message("Start Programming Received - Beginning Test", "SUCCESS")
        
        # Reset for new test
        self.retest_manager.reset_for_new_test()
        self.results_manager.reset_for_new_test()
        self.results_frame.set_all_pending()
        
        # Start text logger session
        text_logger.start_session(
            self.config_frame.serial_no,
            self.config_frame.mac_id
        )
        
        # Update state machine with device info
        self.state_machine.serial_no = self.config_frame.serial_no
        self.state_machine.mac_id = self.config_frame.mac_id
        self.state_machine.bootloader_path = firmware_programmer.bootloader_path
        self.state_machine.test_code_path = firmware_programmer.test_code_path
        self.state_machine.final_fw_path = firmware_programmer.final_firmware_path
        
        # Send start ACK to JIG (TLV format)
        frame = ProtocolHandler.build_start_prog_ack(0x01)
        time.sleep(0.5)
        serial_handler.write_frame(frame)
        
        # Start state machine
        self.state_machine.start()

# NEW
    def _handle_test_complete(self):
        attempt = self.results_manager.record_attempt()
        peri_failed = attempt.peripherals_failed
        dig_failed = attempt.digital_inputs_failed
        relay_failed = attempt.relays_failed
        all_passed = (not peri_failed and not dig_failed and not relay_failed)

        if all_passed:
            self._log_message("Testing PASSED", "SUCCESS")
            self.state_machine.on_testing_complete(True)
        else:
            if peri_failed:
                self._log_message(f"Peripheral Failures: {peri_failed}", "ERROR")
            if dig_failed:
                self._log_message(f"Digital Input Failures: {dig_failed}", "ERROR")
            if relay_failed:
                self._log_message(f"Relay Failures: {relay_failed}", "ERROR")

            self._log_message("Testing FAILED", "ERROR")
            self.state_machine.on_testing_complete(False)

            log_dict = self.results_manager.to_log_dict(
                self.config_frame.serial_no,
                self.config_frame.mac_id,
            )
            excel_logger.log_result(log_dict)

            counts = self.results_frame.get_test_counts()
            text_logger.end_session(
                counts['total'], counts['pass'], counts['fail'], 1, "FAIL"
            )
            self.config_frame.clear_device_info()
            
    # def _handle_test_complete(self):
    #     """Handle test completion (v1.2: called after combined results frame end)"""
    #     # Record attempt
    #     attempt = self.results_manager.record_attempt()
        
    #     all_passed = attempt.overall_pass
    #     attempt_str = f"Attempt {attempt.attempt_number}/{self.retest_manager.max_retries}"
        
    #     if all_passed:
    #         self._log_message(f"[{attempt_str}] Testing PASSED", "SUCCESS")
    #         self.state_machine.on_testing_complete(True)
    #     else:
    #         # Log failures
    #         if attempt.peripherals_failed:
    #             self._log_message(f"[{attempt_str}] Peripheral Failures: {attempt.peripherals_failed}", "ERROR")
    #         if attempt.digital_inputs_failed:
    #             self._log_message(f"[{attempt_str}] Digital Input Failures: {attempt.digital_inputs_failed}", "ERROR")
    #         if attempt.relays_failed:
    #             self._log_message(f"[{attempt_str}] Relay Failures: {attempt.relays_failed}", "ERROR")
            
    #         # Check for retry
    #         if self.retest_manager.should_retry():
    #             self._initiate_retest()
    #         else:
    #             self._log_message(f"Testing FAILED (Max retries: {self.retest_manager.max_retries})", "ERROR")
    #             self._log_message(self.results_manager.get_test_summary_string(), "INFO")
    #             self.state_machine.on_testing_complete(False)
                
    #             # Log to Excel with NOT SET state
    #             log_dict = self.results_manager.to_log_dict(
    #                 self.config_frame.serial_no,
    #                 self.config_frame.mac_id,
    #             )
    #             excel_logger.log_result(log_dict)
                
    #             # End text logger
    #             counts = self.results_frame.get_test_counts()
    #             text_logger.end_session(
    #                 counts['total'],
    #                 counts['pass'],
    #                 counts['fail'],
    #                 self.results_manager.current_attempt,
    #                 "FAIL"
    #             )
    
    # def _initiate_retest(self):
    #     """Initiate automatic retest"""
    #     # FIXED: start_retry increments current_attempt
    #     self.retest_manager.start_retry()
        
    #     mask = self.retest_manager.get_retest_mask()
    #     categories = self.retest_manager.get_tests_to_retry()
        
    #     self._log_message(
    #         f"Initiating retest (attempt {self.retest_manager.current_attempt}/{self.retest_manager.max_retries}): "
    #         f"{[c.name for c in categories]}",
    #         "INFO"
    #     )
        
    #     # Send retest command (TLV format)
    #     frame = ProtocolHandler.build_retest_command(mask)
    #     time.sleep(0.5)
    #     self.serial.write_frame(frame)
        
        # FIXED: Don't send to state machine - it has its own retest handler
        # State machine will detect retest results when they arrive
            
    # def _initiate_retest(self):
    #     """Initiate automatic retest"""
    #     self.retest_manager.start_retry()
        
    #     mask = self.retest_manager.get_retest_mask()
    #     categories = self.retest_manager.get_tests_to_retry()
        
    #     self._log_message(
    #         f"Initiating retry ({self.retest_manager.current_attempt}/{self.retest_manager.max_retries}): "
    #         f"{[c.name for c in categories]}",
    #         "INFO"
    #     )
        
    #     # Reset GUI for retested categories
    #     for cat in categories:
    #         if cat == TestCategory.ALL:
    #             self.results_frame.set_all_pending()
    #             self.results_manager.reset_all()
    #         elif cat == TestCategory.PERIPHERALS:
    #             self.results_frame.set_category_pending("PERIPHERALS")
    #             self.results_manager.reset_peripherals()
    #         elif cat == TestCategory.DIGITAL_INPUTS:
    #             self.results_frame.set_category_pending("DIGITAL_INPUTS")
    #             self.results_manager.reset_digital_inputs()
    #         elif cat == TestCategory.RELAYS:
    #             self.results_frame.set_category_pending("RELAYS")
    #             self.results_manager.reset_relays()
        
    #     # Send retest command (TLV format)
    #     frame = ProtocolHandler.build_retest_command(mask)
    #     time.sleep(0.3)
    #     serial_handler.write_frame(frame)
        
    def _on_test_complete(self, passed: bool):
        """Callback when full test sequence completes"""
        if passed:
            # End text logger with success
            counts = self.results_frame.get_test_counts()
            text_logger.end_session(
                counts['total'],
                counts['pass'],
                counts['fail'],
                self.results_manager.current_attempt,
                "PASS"
            )
            self.config_frame.clear_device_info()
    
    # =========================================================================
    # PROGRAMMING
    # =========================================================================
    
    def _on_program_firmware(self, firmware_type: str):
        """Handle firmware programming request"""
        firmware_programmer.program(firmware_type)
        self._log_message(f"Programming {firmware_type}...", "INFO")

    # def _on_programming_success(self, firmware_type: str):
    #     """Handle programming success"""
    #     self._log_message(f"Success programming {firmware_type}", "SUCCESS")
        
    #     if firmware_type == "BOOTLOADER":
    #         self.state_machine.on_bootloader_result(True)
    #     elif firmware_type == "TEST":
    #         self.state_machine.on_test_firmware_result(True)
    #     elif firmware_type == "FINAL":
    #         self.state_machine.on_final_firmware_result(True)
    
    # def _on_programming_failure(self, firmware_type: str, reason: str):
    #     """Handle programming failure"""
    #     self._log_message(f"Failed programming {firmware_type}: {reason}", "ERROR")
        
    #     if firmware_type == "BOOTLOADER":
    #         self.state_machine.on_bootloader_result(False)
    #     elif firmware_type == "TEST":
    #         self.state_machine.on_test_firmware_result(False)
    #     elif firmware_type == "FINAL":
    #         self.state_machine.on_final_firmware_result(False)

    def _on_programming_success(self, firmware_type: str):
        """Handle programming success - route to main thread"""
        self.message_queue.put('PROG_SUCCESS', firmware_type)

    def _on_programming_failure(self, firmware_type: str, reason: str):
        """Handle programming failure - route to main thread"""
        self.message_queue.put('PROG_FAILURE', (firmware_type, reason))

    # =========================================================================
    # QR SCANNER
    # =========================================================================
    
    def _on_keypress(self, event):
        """Handle keyboard input (QR scanner)"""
        qr_scanner.handle_keypress(event.char)
    
    def _on_serial_scanned(self, serial_no: str):
        """Handle scanned serial number"""
        self.config_frame.serial_no = serial_no
    
    def _on_mac_scanned(self, mac_id: str):
        """Handle scanned MAC ID"""
        self.config_frame.mac_id = mac_id
    
    def _on_duplicate_serial(self, serial_no: str):
        """Handle duplicate serial detection"""
        # Show confirmation dialog
        self._show_duplicate_dialog(serial_no)
    
    def _show_duplicate_dialog(self, serial_no: str):
        """Show dialog for duplicate serial number"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Serial No. Confirmation")
        dialog.geometry("455x140")
        dialog.resizable(False, False)
        
        # Make dialog stay on top and grab focus
        dialog.attributes('-topmost', True)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Force focus to dialog after a short delay
        dialog.after(10, lambda: dialog.focus_force())
        
        ctk.CTkLabel(
            dialog,
            text="Device already tested. Do you want to retest?",
            font=("Calibri", 18)
        ).grid(row=0, column=0, columnspan=2, pady=20, padx=20, sticky="w")
        
        def on_retest():
            self.config_frame.serial_no = serial_no
            dialog.destroy()
        
        ctk.CTkButton(
            dialog, width=150, text='Retest',
            command=on_retest,
            font=("Calibri", 18)
        ).grid(row=1, column=0, pady=20, padx=20, sticky="ew")
        
        ctk.CTkButton(
            dialog, width=150, text='Cancel',
            command=dialog.destroy,
            font=("Calibri", 18)
        ).grid(row=1, column=1, pady=20, padx=20, sticky="ew")
        
        # Center dialog on parent window
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
    
    # =========================================================================
    # DEVELOPER MODE
    # =========================================================================
    
    def _load_dev_defaults(self):
        """Load developer default values"""
        self.config_frame.serial_no = DEV_DEFAULT_SERIAL_NO
        self.config_frame.mac_id = DEV_DEFAULT_MAC_ID
    
    def _clear_dev_ids(self):
        """Clear serial and MAC fields"""
        self.config_frame.clear_device_info()
    
    def _user_reset(self):
        """Reset all state and clear device info (utility reset button)"""
        self.state_machine.reset()
        self.retest_manager.reset_for_new_test()
        self.results_manager.reset_for_new_test()
        self.results_frame.reset_all()
        serial_handler.clear_rx_buffer()
        self.config_frame.clear_device_info()
        self._log_message("Utility reset", "INFO")

        if DEVELOPER_MODE_ENABLED:
            self.developer_frame.update_status()

    def _reset_utility(self):
        """Reset utility to defaults"""
        self.state_machine.reset()
        self.retest_manager.reset_for_new_test()
        self.results_manager.reset_for_new_test()
        self.results_frame.reset_all()
        serial_handler.clear_rx_buffer()
        self._load_dev_defaults()

        if DEVELOPER_MODE_ENABLED:
            self.developer_frame.update_status()
    
    # def _manual_retest(self, strategy: RetestStrategy):
    #     """Handle manual retest request"""
    #     if not self.results_manager.test_history:
    #         self._log_message("No previous test to retry", "ERROR")
    #         return
        
    #     self.retest_manager.retest_strategy = strategy
    #     self._initiate_retest()
    
    # def _specific_retest(self, category: TestCategory):
    #     """Handle specific category retest"""
    #     self.retest_manager.set_specific_test(category)
    #     self._initiate_retest()
    
    def _show_test_summary(self):
        """Show test summary in logs"""
        summary = self.results_manager.get_test_summary_string()
        self._log_message(summary, "INFO")
    
    # =========================================================================
    # MESSAGE QUEUE
    # =========================================================================
    
    def _check_queue(self):
        """Process pending messages (called from main loop)"""
        self.message_queue.process_pending()
        self.root.after(100, self._check_queue)
    
    def _handle_dut_reset(self, data):
        """Handle DUT reset message"""
        # This would be called from state machine
        pass
    
    def _handle_gui_update(self, data):
        """Handle GUI update message"""
        self.results_frame.update_from_results()
    
    def _handle_log_message(self, data):
        """Handle log message from queue"""
        if data:
            message, level = data
            self.logs_textbox.log(message, level)

    def _handle_test_complete_safe(self, data):
        """Handle test completion on main thread (safe for GUI access)"""
        self._handle_test_complete()

    def _handle_comm_failed_safe(self, data):
        """Handle comm failure on main thread"""
        self.state_machine.on_comm_failed()    

    def _handle_start_test_safe(self, data):
        """Handle start test on main thread"""
        self._start_test_sequence()
        
    def _handle_prog_success_safe(self, firmware_type):
        """Handle programming success on main thread"""
        self._log_message(f"Success programming {firmware_type}", "SUCCESS")
        if firmware_type == "BOOTLOADER":
            self.state_machine.on_bootloader_result(True)
        elif firmware_type == "TEST":
            self.state_machine.on_test_firmware_result(True)
        elif firmware_type == "FINAL":
            self.state_machine.on_final_firmware_result(True)

    def _handle_prog_failure_safe(self, data):
        """Handle programming failure on main thread"""
        firmware_type, reason = data
        self._log_message(f"Failed programming {firmware_type}: {reason}", "ERROR")
        if firmware_type == "BOOTLOADER":
            self.state_machine.on_bootloader_result(False)
        elif firmware_type == "TEST":
            self.state_machine.on_test_firmware_result(False)
        elif firmware_type == "FINAL":
            self.state_machine.on_final_firmware_result(False)
    # =========================================================================
    # LOGGING
    # =========================================================================
    
    def _log_message(self, message: str, level: str = "INFO"):
        """Log a message to the textbox"""
        with_time = level != "INFO" or not message.startswith("=")
        self.logs_textbox.log(message, level, with_time)
        
        # Also log to text logger if session active
        if text_logger.is_active:
            text_logger.log(level, message)
    
    def _log_startup(self):
        """Log startup information"""
        self._log_message(f"=== {self.product_config.product_name} Testing Utility v{VERSION} ===", "INFO")
        # self._log_message("Protocol v1.2: TLV Format + Combined Results Frame", "INFO")
        # self._log_message(
        #     f"Config: {len(self.results_manager.peripherals)} peripherals, "
        #     f"{len(self.results_manager.digital_inputs)} digital inputs, "
        #     f"{len(self.results_manager.relays)} relays",
        #     "INFO"
        # )
        
        # Log TLV parser config
        bitmap_info = self.tlv_parser.get_bitmap_summary()
        # self._log_message(
        #     f"TLV Parser: PERI={bitmap_info['peripheral_bytes']}B, "
        #     f"DIG={bitmap_info['digital_input_bytes']}B, "
        #     f"RELAY={bitmap_info['relay_bytes']}B",
        #     "INFO"
        # )
        
        if DEVELOPER_MODE_ENABLED:
            self._log_message(">>> DEVELOPER MODE ACTIVE <<<", "ERROR")
            self._log_message(
                f"Max Retries: {self.retest_manager.max_retries} | "
                f"Strategy: {self.retest_manager.retest_strategy.name}",
                "INFO"
            )
        # else:
        #     self._log_message(
        #         f"Auto-Retry: {USER_MODE_MAX_RETRIES} attempts | Strategy: FAILED_ONLY",
        #         "INFO"
        #     )
        
        self._log_message("=" * 35, "INFO")
    
    # =========================================================================
    # RUN
    # =========================================================================
    
    def run(self):
        """Start the main application loop"""
        self.root.mainloop()
