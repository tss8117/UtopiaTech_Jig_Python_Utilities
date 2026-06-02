# ============================================================================
# JIG ONE v1.1 - Configuration Frame
# ============================================================================

import customtkinter as ctk
from tkinter import StringVar, filedialog
from typing import Callable, Optional
import os

from config.settings import DEFAULT_COLOR, DEVELOPER_MODE_ENABLED, FIRMWARE_DIR, BASE_DIR
from models.product_config import ProductConfig
from services.programmer import FirmwareProgrammer


class ConfigFrame(ctk.CTkFrame):
    """
    Frame for firmware selection and device configuration.
    """
    
    def __init__(
        self,
        master,
        product_config: ProductConfig,
        programmer: FirmwareProgrammer,
        on_log: Optional[Callable[[str, str], None]] = None,
        on_program: Optional[Callable[[str], None]] = None,
        on_reset: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)

        self.product_config = product_config
        self.programmer = programmer
        self._on_log = on_log
        self._on_program = on_program
        self._on_reset = on_reset
        
        # Variables
        self.bootloader_var = StringVar()
        self.testcode_var = StringVar()
        self.finalcode_var = StringVar()
        self.serial_no_var = StringVar()
        self.mac_id_var = StringVar()
        
        # Build UI
        self._build_ui()
        
        # Auto-load firmware from config
        self._auto_load_firmware()
    
    def _build_ui(self):
        """Build the frame UI"""
        # Entry state based on mode
        entry_state = 'normal' if DEVELOPER_MODE_ENABLED else 'disabled'
        
        # Configure grid columns
        self.grid_columnconfigure(0, weight=0)  # Label
        self.grid_columnconfigure(1, weight=1)  # Entry (expandable)
        self.grid_columnconfigure(2, weight=0)  # Extra space
        self.grid_columnconfigure(3, weight=0)  # Browse button
        self.grid_columnconfigure(4, weight=0)  # Program button
        
        # Row 0: Bootloader
        ctk.CTkLabel(
            self, text="Bootloader File", font=("Calibri", 16)
        ).grid(row=0, column=0, pady=10, padx=10, sticky="w")
        
        ctk.CTkEntry(
            self, textvariable=self.bootloader_var,
            state="readonly", font=("Calibri", 16)
        ).grid(row=0, column=1, pady=10, padx=10, sticky="ew")
        
        ctk.CTkButton(
            self, width=80, text='Browse',
            command=lambda: self._select_firmware("BOOTLOADER"),
            font=("Calibri", 14), fg_color=DEFAULT_COLOR
        ).grid(row=0, column=3, pady=10, padx=5)
        
        ctk.CTkButton(
            self, width=80, text='Program',
            command=lambda: self._program_firmware("BOOTLOADER"),
            font=("Calibri", 14), fg_color=DEFAULT_COLOR
        ).grid(row=0, column=4, pady=10, padx=10)
        
        # Row 1: Test Firmware
        ctk.CTkLabel(
            self, text="Test Firmware File", font=("Calibri", 16)
        ).grid(row=1, column=0, pady=10, padx=10, sticky="w")
        
        ctk.CTkEntry(
            self, textvariable=self.testcode_var,
            state="readonly", font=("Calibri", 16)
        ).grid(row=1, column=1, pady=10, padx=10, sticky="ew")
        
        ctk.CTkButton(
            self, width=80, text='Browse',
            command=lambda: self._select_firmware("TEST"),
            font=("Calibri", 14), fg_color=DEFAULT_COLOR
        ).grid(row=1, column=3, pady=10, padx=5)
        
        ctk.CTkButton(
            self, width=80, text='Program',
            command=lambda: self._program_firmware("TEST"),
            font=("Calibri", 14), fg_color=DEFAULT_COLOR
        ).grid(row=1, column=4, pady=10, padx=10)
        
        # Row 2: Final Firmware
        ctk.CTkLabel(
            self, text="Final Firmware File", font=("Calibri", 16)
        ).grid(row=2, column=0, pady=10, padx=10, sticky="w")
        
        ctk.CTkEntry(
            self, textvariable=self.finalcode_var,
            state="readonly", font=("Calibri", 16)
        ).grid(row=2, column=1, pady=10, padx=10, sticky="ew")
        
        ctk.CTkButton(
            self, width=80, text='Browse',
            command=lambda: self._select_firmware("FINAL"),
            font=("Calibri", 14), fg_color=DEFAULT_COLOR
        ).grid(row=2, column=3, pady=10, padx=5)
        
        ctk.CTkButton(
            self, width=80, text='Program',
            command=lambda: self._program_firmware("FINAL"),
            font=("Calibri", 14), fg_color=DEFAULT_COLOR
        ).grid(row=2, column=4, pady=10, padx=10)
        
        # Row 3: MAC ID and Serial No
        ctk.CTkLabel(
            self, text="MAC ID", font=("Calibri", 16)
        ).grid(row=3, column=0, pady=10, padx=10, sticky="w")
        
        ctk.CTkEntry(
            self, textvariable=self.mac_id_var,
            state=entry_state, font=("Calibri", 16)
        ).grid(row=3, column=1, pady=10, padx=10, sticky="ew")
        
        ctk.CTkLabel(
            self, text="Serial No.", font=("Calibri", 16)
        ).grid(row=3, column=3, pady=10, padx=5, sticky="w")
        
        ctk.CTkEntry(
            self, width=120, textvariable=self.serial_no_var,
            state=entry_state, font=("Calibri", 16)
        ).grid(row=3, column=4, pady=10, padx=10, sticky="ew")

        # Row 4: Reset button (below Serial No)
        ctk.CTkButton(
            self, text="Reset", font=("Calibri", 14),
            fg_color="#C0392B", hover_color="#922B21",
            command=self._on_reset_clicked
        ).grid(row=4, column=3, columnspan=2, pady=(0, 10), padx=10, sticky="ew")
    
    def _on_reset_clicked(self):
        if self._on_reset:
            self._on_reset()

    def _select_firmware(self, firmware_type: str):
        """Open file dialog to select firmware"""
        filetypes = (
            ('HEX files', '*.hex'),
            ('BIN files', '*.bin'),
            ('All files', '*.*')
        )
        
        initial_dir = FIRMWARE_DIR if os.path.exists(FIRMWARE_DIR) else BASE_DIR
        
        filepath = filedialog.askopenfilename(
            title=f'Select {firmware_type} Firmware',
            initialdir=initial_dir,
            filetypes=filetypes
        )
        
        if not filepath:
            return
        
        filename = os.path.basename(filepath)
        
        # Try to get relative path for config storage
        try:
            rel_path = os.path.relpath(filepath, BASE_DIR)
        except ValueError:
            rel_path = filepath
        
        if firmware_type == "BOOTLOADER":
            if self.programmer.set_bootloader(filepath):
                self.bootloader_var.set(filename)
                self.product_config.save_firmware_path("BOOTLOADER", rel_path)
                self._log(f"Bootloader selected: {filename}", "INFO")
            
        elif firmware_type == "TEST":
            if self.programmer.set_test_code(filepath):
                self.testcode_var.set(filename)
                self.product_config.save_firmware_path("TEST", rel_path)
                self._log(f"Test firmware selected: {filename}", "INFO")
            
        elif firmware_type == "FINAL":
            if self.programmer.set_final_firmware(filepath):
                self.finalcode_var.set(filename)
                self.product_config.save_firmware_path("FINAL", rel_path)
                self._log(f"Final firmware selected: {filename}", "INFO")
    
    def _program_firmware(self, firmware_type: str):
        """Start firmware programming"""
        if firmware_type == "BOOTLOADER" and not self.bootloader_var.get():
            self._log("Select bootloader file first", "ERROR")
            return
        elif firmware_type == "TEST" and not self.testcode_var.get():
            self._log("Select test firmware file first", "ERROR")
            return
        elif firmware_type == "FINAL" and not self.finalcode_var.get():
            self._log("Select final firmware file first", "ERROR")
            return
        
        if self._on_program:
            self._on_program(firmware_type)
        else:
            self.programmer.program(firmware_type)
            self._log(f"Programming {firmware_type}...", "INFO")
    
    def _auto_load_firmware(self):
        """Auto-load firmware paths from product config"""
        fw_paths = self.product_config.get_firmware_paths()
        loaded = 0
        
        # Bootloader
        boot_path = fw_paths["bootloader"].path
        if boot_path:
            full_path = os.path.join(BASE_DIR, boot_path) if not os.path.isabs(boot_path) else boot_path
            if os.path.exists(full_path):
                if self.programmer.set_bootloader(full_path):
                    self.bootloader_var.set(os.path.basename(full_path))
                    loaded += 1
        
        # Test Code
        test_path = fw_paths["test_code"].path
        if test_path:
            full_path = os.path.join(BASE_DIR, test_path) if not os.path.isabs(test_path) else test_path
            if os.path.exists(full_path):
                if self.programmer.set_test_code(full_path):
                    self.testcode_var.set(os.path.basename(full_path))
                    loaded += 1
        
        # Final Firmware
        final_path = fw_paths["final_firmware"].path
        if final_path:
            full_path = os.path.join(BASE_DIR, final_path) if not os.path.isabs(final_path) else final_path
            if os.path.exists(full_path):
                if self.programmer.set_final_firmware(full_path):
                    self.finalcode_var.set(os.path.basename(full_path))
                    loaded += 1
        
        if loaded > 0:
            print(f"[CONFIG] Auto-loaded {loaded}/3 firmware paths")
    
    def _log(self, message: str, level: str = "INFO"):
        """Log a message"""
        if self._on_log:
            self._on_log(message, level)
    
    # Public properties for external access
    @property
    def serial_no(self) -> str:
        return self.serial_no_var.get()
    
    @serial_no.setter
    def serial_no(self, value: str):
        self.serial_no_var.set(value)
    
    @property
    def mac_id(self) -> str:
        return self.mac_id_var.get()
    
    @mac_id.setter
    def mac_id(self, value: str):
        self.mac_id_var.set(value)
    
    def has_all_firmware(self) -> bool:
        """Check if all firmware files are selected"""
        return bool(
            self.bootloader_var.get() and
            self.testcode_var.get() and
            self.finalcode_var.get()
        )
    
    def has_device_info(self) -> bool:
        """Check if serial and MAC are set"""
        return bool(self.serial_no_var.get() and self.mac_id_var.get())
    
    def clear_device_info(self):
        """Clear serial and MAC fields"""
        self.serial_no_var.set("")
        self.mac_id_var.set("")
