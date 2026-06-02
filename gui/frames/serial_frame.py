# ============================================================================
# JIG ONE v1.1 - Serial Connection Frame
# ============================================================================

import customtkinter as ctk
from tkinter import StringVar
from typing import Callable, Optional, List

from config.settings import DEFAULT_COLOR
from core.serial_handler import SerialHandler, SerialPortInfo


class SerialFrame(ctk.CTkFrame):
    """
    Frame for serial port connection controls.
    """
    
    def __init__(
        self,
        master,
        serial_handler: SerialHandler,
        on_log: Optional[Callable[[str, str], None]] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)
        
        self.serial_handler = serial_handler
        self._on_log = on_log
        
        # Variables
        self._port_var = StringVar()
        self._ports_list: List[str] = []
        
        # Build UI
        self._build_ui()
        
        # Initial port scan
        self.refresh_ports()


    def _build_ui(self):
        """Build the frame UI"""
        # Configure grid columns
        self.grid_columnconfigure(0, weight=0)  # Label
        self.grid_columnconfigure(1, weight=1)  # Combobox (expandable)
        self.grid_columnconfigure(2, weight=0)  # Refresh button
        self.grid_columnconfigure(3, weight=0)  # Connect button
        
        # Label
        ctk.CTkLabel(
            self,
            text="RS485 Port",
            font=("Calibri", 16)
        ).grid(row=0, column=0, pady=15, padx=15, sticky="w")
        
        # Port combobox
        self._port_combobox = ctk.CTkComboBox(
            self,
            variable=self._port_var,
            values=[],
            state="readonly",
            font=("Calibri", 16)
        )
        self._port_combobox.grid(row=0, column=1, pady=15, padx=10, sticky="ew")
        
        # Refresh button
        ctk.CTkButton(
            self,
            width=35,
            text='R',
            command=self.refresh_ports,
            font=("Calibri", 16),
            fg_color=DEFAULT_COLOR
        ).grid(row=0, column=2, pady=15, padx=5)
        
        # Connect/Disconnect button
        self._connect_button = ctk.CTkButton(
            self,
            width=120,
            text='Disconnected',
            command=self._toggle_connection,
            font=("Calibri", 16),
            fg_color=DEFAULT_COLOR,
            hover_color='grey'
        )
        self._connect_button.grid(row=0, column=3, pady=15, padx=15)
    
    # def refresh_ports(self):
    #     """Refresh available serial ports"""
    #     ports = self.serial_handler.list_ports()
    #     self._ports_list = [p.display_name for p in ports]
        
    #     self._port_combobox.configure(values=self._ports_list)
        
    #     if self._ports_list:
    #         self._port_var.set(self._ports_list[0])

    # NEW
    def refresh_ports(self):
        ports = self.serial_handler.list_ports()
        self._ports_list = [p.display_name for p in ports]
        self._port_combobox.configure(values=self._ports_list)

        if self._ports_list:
            self._port_var.set(self._ports_list[0])

        # If already connected, update button in case port list refreshed
        if self.serial_handler.is_connected:
            self._connect_button.configure(
                text='Connected',
                fg_color='#8dff50',
                text_color='black'
            )
        else:
            self._connect_button.configure(
                text='Disconnected',
                fg_color=DEFAULT_COLOR,
                text_color='white'
            )

    # NEW
    def auto_connect(self):
        if self.serial_handler.is_connected:
            return

        ports = self.serial_handler.list_ports()
        self._ports_list = [p.display_name for p in ports]
        self._port_combobox.configure(values=self._ports_list)

        if not self._ports_list:
            self._log("No serial ports found, retrying...", "WARNING")
            self.after(2000, self.auto_connect)
            return

        # Prefer USB serial ports over built-in ones (ttyS0, ttyAMA0 etc.)
        selected_port = self._pick_preferred_port(ports)

        if selected_port is None:
            self._log("No USB serial port found, retrying...", "WARNING")
            self.after(2000, self.auto_connect)
            return

        self._port_var.set(selected_port.display_name)
        port = selected_port.device

        if self.serial_handler.connect(port):
            self._connect_button.configure(
                text='Connected',
                fg_color='#8dff50',
                text_color='black'
            )
            self._log(f"Auto-connected to {port}", "SUCCESS")
        else:
            self._log(f"Auto-connect failed on {port}, retrying...", "WARNING")
            self.after(2000, self.auto_connect)


    def _pick_preferred_port(self, ports):
        """
        Pick the best available port.
        Priority:
        1. ttyUSB* ports (USB-to-serial adapters)
        2. ttyACM* ports (USB CDC devices)
        3. Anything with 'USB' in the product/description
        4. Skip ttyS* and ttyAMA* (built-in UART)
        Returns None if no suitable port found.
        """
        USB_PREFERRED = ('ttyUSB', 'ttyACM')
        BUILTIN_SKIP  = ('ttyS', 'ttyAMA', 'ttySerial')

        usb_ports = []
        fallback_ports = []

        for p in ports:
            device = p.device  # e.g. /dev/ttyUSB0

            # Skip known built-in ports
            if any(device.endswith(skip) or f'/{skip}' in device 
                for skip in BUILTIN_SKIP):
                continue

            # Prefer ttyUSB / ttyACM
            if any(pref in device for pref in USB_PREFERRED):
                usb_ports.append(p)
            elif 'USB' in (p.product + p.description).upper():
                fallback_ports.append(p)

        if usb_ports:
            return usb_ports[0]
        if fallback_ports:
            return fallback_ports[0]
        return None

    def _toggle_connection(self):
        """Toggle serial connection"""
        if self.serial_handler.is_connected:
            self._disconnect()
        else:
            self._connect()
    
    def _connect(self):
        """Connect to selected port"""
        port_display = self._port_var.get()
        
        if not port_display:
            self._log("Select a serial port first", "ERROR")
            return
        
        # Extract actual port device from display string
        port = port_display.split(" | ")[0]
        
        if self.serial_handler.connect(port):
            self._connect_button.configure(
                text='Connected',
                fg_color='#8dff50',
                text_color='black'
            )
            self._log("Serial Connected", "SUCCESS")
        else:
            self._log("Failed to connect", "ERROR")
    
    # def _disconnect(self):
    #     """Disconnect from serial port"""
    #     self.serial_handler.disconnect()
    #     self._connect_button.configure(
    #         text='Disconnected',
    #         fg_color=DEFAULT_COLOR,
    #         text_color='white'
    #     )
    #     self._log("Serial Disconnected", "INFO")

    # NEW
    def _disconnect(self):
        self.serial_handler.disconnect()
        self._connect_button.configure(
            text='Disconnected',
            fg_color=DEFAULT_COLOR,
            text_color='white'
        )
        self._log("Serial Disconnected", "INFO")
        
        # Start polling to auto-reconnect
        self.after(2000, self._auto_connect)

    
    def _log(self, message: str, level: str = "INFO"):
        """Log a message"""
        if self._on_log:
            self._on_log(message, level)
    
    @property
    def is_connected(self) -> bool:
        """Check if connected"""
        return self.serial_handler.is_connected