# ============================================================================
# JIG ONE v1.1 - Firmware Programmer Service
# ============================================================================
# Handles OpenOCD-based firmware programming
# ============================================================================

import os
import subprocess
from threading import Thread, Event
from typing import Optional, Callable
import time
import platform
from config.settings import (
    PROGRAMMING_TIMEOUT,
    BASE_DIR,
    BOOTLOADER_OPENOCD_TEMPLATE,
    FIRMWARE_OPENOCD_TEMPLATE,
)


class FirmwareProgrammer:
    """
    Handles firmware programming via OpenOCD.
    
    Features:
    - Async programming with callbacks
    - Log file parsing for success/failure detection
    - OpenOCD config file generation from templates
    """
    
    def __init__(self):
        # Current programming state
        self._programming_thread: Optional[Thread] = None
        self._stop_event = Event()
        
        # Firmware paths
        self.bootloader_path: str = ""
        self.test_code_path: str = ""
        self.final_firmware_path: str = ""
        
        # OpenOCD log paths (auto-generated)
        self._bootloader_log: str = ""
        self._test_code_log: str = ""
        self._final_fw_log: str = ""
        
        # Callbacks
        self._on_success: Optional[Callable[[str], None]] = None
        self._on_failure: Optional[Callable[[str, str], None]] = None
        self._on_log: Optional[Callable[[str], None]] = None
    
    # ========================================================================
    # OPENOCD CONFIG GENERATION
    # ========================================================================
    
    @staticmethod
    def create_openocd_config(
        hex_filename: str,
        template_path: str,
        output_path: str
    ) -> bool:
        """
        Create OpenOCD config file from template.
        
        Args:
            hex_filename: Name of the hex file to program
            template_path: Path to OpenOCD config template
            output_path: Path to write generated config
            
        Returns:
            True if successful
        """
        try:
            with open(template_path, 'r') as f:
                template = f.read()
            
            # Replace placeholder with actual filename
            config = template.replace("HEX_FILE_HERE", hex_filename)
            
            with open(output_path, 'w') as f:
                f.write(config)
            
            print(f"[PROG] Created OpenOCD config: {output_path}")
            return True
            
        except Exception as e:
            print(f"[PROG] Error creating OpenOCD config: {e}")
            return False
    
    # ========================================================================
    # FIRMWARE PATH SETUP
    # ========================================================================
    
    def set_bootloader(self, hex_path: str) -> bool:
        if not os.path.exists(hex_path):
            print(f"[PROG] Bootloader file not found: {hex_path}")
            return False
        
        self.bootloader_path = os.path.dirname(hex_path) + '/'
        filename = os.path.basename(hex_path)
        
        # Create OpenOCD config with UNIQUE NAME
        config_path = self.bootloader_path + 'openocd_bootloader.cfg'  # ← Changed!
        if not self.create_openocd_config(filename, BOOTLOADER_OPENOCD_TEMPLATE, config_path):
            return False
        
        # Setup log path
        log_dir = self.bootloader_path + 'Bootloader_Logs/'
        os.makedirs(log_dir, exist_ok=True)
        self._bootloader_log = log_dir + 'bootloader_cli_log.txt'
        
        print(f"[PROG] Bootloader set: {filename}")
        return True

    def set_test_code(self, hex_path: str) -> bool:
        if not os.path.exists(hex_path):
            print(f"[PROG] Test code file not found: {hex_path}")
            return False
        
        self.test_code_path = os.path.dirname(hex_path) + '/'
        filename = os.path.basename(hex_path)
        
        config_path = self.test_code_path + 'openocd_test.cfg'  # ← Changed!
        if not self.create_openocd_config(filename, FIRMWARE_OPENOCD_TEMPLATE, config_path):
            return False
        
        log_dir = self.test_code_path + 'Test_Code_Logs/'
        os.makedirs(log_dir, exist_ok=True)
        self._test_code_log = log_dir + 'test_code_cli_log.txt'
        
        print(f"[PROG] Test code set: {filename}")
        return True

    def set_final_firmware(self, hex_path: str) -> bool:
        if not os.path.exists(hex_path):
            print(f"[PROG] Final firmware file not found: {hex_path}")
            return False
        
        self.final_firmware_path = os.path.dirname(hex_path) + '/'
        filename = os.path.basename(hex_path)
        
        config_path = self.final_firmware_path + 'openocd_final.cfg'  # ← Changed!
        if not self.create_openocd_config(filename, FIRMWARE_OPENOCD_TEMPLATE, config_path):
            return False
        
        log_dir = self.final_firmware_path + 'Final_Code_Logs/'
        os.makedirs(log_dir, exist_ok=True)
        self._final_fw_log = log_dir + 'final_code_cli_log.txt'
        
        print(f"[PROG] Final firmware set: {filename}")
        return True
    
    # ========================================================================
    # PROGRAMMING
    # ========================================================================
    
    def program(self, firmware_type: str) -> bool:
        """
        Start asynchronous firmware programming.
        """
        # Get paths and CONFIG FILE based on type
        if firmware_type == "BOOTLOADER":
            if not self.bootloader_path:
                self._log("Bootloader path not set")
                return False
            work_dir = self.bootloader_path
            log_path = self._bootloader_log
            config_file = 'openocd_bootloader.cfg'  # ← Use correct config!
            
        elif firmware_type == "TEST":
            if not self.test_code_path:
                self._log("Test code path not set")
                return False
            work_dir = self.test_code_path
            log_path = self._test_code_log
            config_file = 'openocd_test.cfg'  # ← Use correct config!
            
        elif firmware_type == "FINAL":
            if not self.final_firmware_path:
                self._log("Final firmware path not set")
                return False
            work_dir = self.final_firmware_path
            log_path = self._final_fw_log
            config_file = 'openocd_final.cfg'  # ← Use correct config!
        else:
            self._log(f"Unknown firmware type: {firmware_type}")
            return False
        
        # Kill any lingering openocd from a previous session before starting
        self._kill_openocd()
        time.sleep(1.5)  # Allow USB to re-enumerate after killing previous instance

        # Clear log file
        try:
            with open(log_path, 'w') as f:
                pass
        except Exception as e:
            self._log(f"Error clearing log file: {e}")

        if platform.system() == "Windows":
            # Use the specific config file
            command = f'cd /d "{work_dir}" && openocd -f {config_file} > "{log_path}" 2>&1'
        else:
            # Use the specific config file
            command = f'cd {work_dir} && sudo timeout {PROGRAMMING_TIMEOUT}s openocd -f {config_file} 2>&1 | tee {log_path}'
        
        # Start programming...
        self._stop_event.clear()
        self._programming_thread = Thread(
            target=self._program_async,
            args=(firmware_type, command, log_path),
            daemon=True
        )
        self._programming_thread.start()
        
        self._log(f"Started programming {firmware_type}")
        return True
    
    def _program_async(self, firmware_type: str, command: str, log_path: str):
        """Async programming thread"""
        proc = None
        try:
            proc = subprocess.Popen(command, shell=True)

            # Monitor log file for result
            timeout_start = time.time()

            while time.time() - timeout_start < PROGRAMMING_TIMEOUT:
                if self._stop_event.is_set():
                    self._log(f"{firmware_type} programming cancelled")
                    return

                # Check log file for result
                result = self._check_programming_result(log_path)

                if result == "SUCCESS":
                    self._log(f"{firmware_type} programming successful")
                    if self._on_success:
                        self._on_success(firmware_type)
                    return

                elif result == "FAILED":
                    self._log(f"{firmware_type} programming failed")
                    if self._on_failure:
                        self._on_failure(firmware_type, "Programming verification failed")
                    return

                time.sleep(0.5)

            # Timeout — kill the openocd process so it releases the ST-Link USB lock
            self._kill_openocd(proc)
            self._log(f"{firmware_type} programming timeout")
            if self._on_failure:
                self._on_failure(firmware_type, "Programming timeout")

        except Exception as e:
            self._kill_openocd(proc)
            self._log(f"{firmware_type} programming error: {e}")
            if self._on_failure:
                self._on_failure(firmware_type, str(e))
    
    def _check_programming_result(self, log_path: str) -> str:
        """
        Check programming result from log file.
        
        Returns:
            'SUCCESS', 'FAILED', or 'PENDING'
        """
        try:
            with open(log_path, 'r') as f:
                content = f.read()
            
            # Check for success first
            if "** Verified OK **" in content:
                return "SUCCESS"
            
            # Check for fatal errors (not warnings)
            fatal_errors = [
                "Error: flash write failed",
                "Error: timed out",
                "** Programming Failed **",
            ]
            
            for error in fatal_errors:
                if error in content:
                    return "FAILED"
            
            return "PENDING"
            
        except Exception:
            return "PENDING"
    
    # ========================================================================
    # FLASH ERASE
    # ========================================================================

    def flash_erase(self) -> bool:
        """Perform full flash erase via OpenOCD (mass erase all sectors)."""
        erase_config = (
            "source [find interface/stlink.cfg]\n"
            "transport select swd\n"
            "source [find target/stm32f0x.cfg]\n"
            "reset_config srst_nogate\n"
            "adapter speed 500\n"
            "init\n"
            "targets\n"
            "reset halt\n"
            "flash erase_sector 0 0 last\n"
            "reset\n"
            "shutdown\n"
        )

        work_dir = BASE_DIR
        erase_cfg_path = os.path.join(BASE_DIR, 'openocd_erase.cfg')
        log_dir = os.path.join(BASE_DIR, 'Erase_Logs')
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, 'flash_erase_log.txt')

        try:
            with open(erase_cfg_path, 'w') as f:
                f.write(erase_config)
        except Exception as e:
            self._log(f"Error creating erase config: {e}")
            return False

        try:
            with open(log_path, 'w'):
                pass
        except Exception as e:
            self._log(f"Error clearing erase log: {e}")

        if platform.system() == "Windows":
            command = f'cd /d "{work_dir}" && openocd -f openocd_erase.cfg > "{log_path}" 2>&1'
        else:
            command = f'cd {work_dir} && sudo timeout {PROGRAMMING_TIMEOUT}s openocd -f openocd_erase.cfg 2>&1 | tee {log_path}'

        self._stop_event.clear()
        self._programming_thread = Thread(
            target=self._erase_async,
            args=(command, log_path),
            daemon=True
        )
        self._programming_thread.start()
        self._log("Started full flash erase")
        return True

    def _erase_async(self, command: str, log_path: str):
        """Async flash erase thread"""
        proc = None
        try:
            proc = subprocess.Popen(command, shell=True)

            timeout_start = time.time()
            while time.time() - timeout_start < PROGRAMMING_TIMEOUT:
                if self._stop_event.is_set():
                    self._log("Flash erase cancelled")
                    return

                result = self._check_erase_result(log_path)

                if result == "SUCCESS":
                    self._log("Flash erase successful")
                    if self._on_success:
                        self._on_success("ERASE")
                    return
                elif result == "FAILED":
                    self._log("Flash erase failed")
                    if self._on_failure:
                        self._on_failure("ERASE", "Flash erase failed")
                    return

                time.sleep(0.5)

            self._kill_openocd(proc)
            self._log("Flash erase timeout")
            if self._on_failure:
                self._on_failure("ERASE", "Flash erase timeout")

        except Exception as e:
            self._kill_openocd(proc)
            self._log(f"Flash erase error: {e}")
            if self._on_failure:
                self._on_failure("ERASE", str(e))

    def _check_erase_result(self, log_path: str) -> str:
        """Check erase result from log file. Returns 'SUCCESS', 'FAILED', or 'PENDING'."""
        try:
            with open(log_path, 'r') as f:
                content = f.read()

            if "shutdown command invoked" in content:
                return "SUCCESS"

            fatal_errors = [
                "Error: flash erase failed",
                "Error: timed out",
                "Error: couldn't bind",
                "** Programming Failed **",
            ]
            for error in fatal_errors:
                if error in content:
                    return "FAILED"

            return "PENDING"
        except Exception:
            return "PENDING"

    def _kill_openocd(self, proc=None):
        """Kill a specific openocd process and any orphaned openocd processes."""
        if proc is not None:
            try:
                proc.kill()
                proc.wait(timeout=3)
            except Exception:
                pass
        try:
            if platform.system() == "Windows":
                subprocess.run(['taskkill', '/F', '/IM', 'openocd.exe'],
                               capture_output=True, timeout=5)
            else:
                subprocess.run(['sudo', 'pkill', '-f', 'openocd'],
                               capture_output=True, timeout=5)
        except Exception:
            pass

    def cancel(self):
        """Cancel ongoing programming"""
        self._stop_event.set()
        self._kill_openocd()
    
    # ========================================================================
    # CALLBACKS
    # ========================================================================
    
    def on_success(self, callback: Callable[[str], None]):
        """Register callback for programming success"""
        self._on_success = callback
    
    def on_failure(self, callback: Callable[[str, str], None]):
        """Register callback for programming failure"""
        self._on_failure = callback
    
    def on_log(self, callback: Callable[[str], None]):
        """Register callback for log messages"""
        self._on_log = callback
    
    def _log(self, message: str):
        """Internal logging"""
        print(f"[PROG] {message}")
        if self._on_log:
            self._on_log(message)
    
    # ========================================================================
    # STATUS
    # ========================================================================
    
    @property
    def is_programming(self) -> bool:
        """Check if programming is in progress"""
        return (self._programming_thread is not None and 
                self._programming_thread.is_alive())
    
    def get_status(self) -> dict:
        """Get current programmer status"""
        return {
            'bootloader_path': self.bootloader_path,
            'test_code_path': self.test_code_path,
            'final_firmware_path': self.final_firmware_path,
            'is_programming': self.is_programming,
        }


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================
firmware_programmer = FirmwareProgrammer()
