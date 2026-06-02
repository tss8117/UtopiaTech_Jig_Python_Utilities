# ============================================================================
# JIG ONE v1.1 - Log Textbox Widget
# ============================================================================

import customtkinter as ctk
from datetime import datetime
from typing import Optional


class LogTextbox(ctk.CTkTextbox):
    """
    A textbox widget for displaying color-coded log messages.
    """
    
    def __init__(
        self,
        master,
        font: tuple = ("Calibri", 18),
        fg_color: str = "white",
        **kwargs
    ):
        super().__init__(
            master,
            font=font,
            fg_color=fg_color,
            state='disabled',
            **kwargs
        )
        
        # Configure tags for different log types
        self.tag_config('ERROR', foreground="red")
        self.tag_config('SUCCESS', foreground="green")
        self.tag_config('WARNING', foreground="orange")
        self.tag_config('INFO', foreground="black")
        self.tag_config('DEBUG', foreground="gray")
        self.tag_config('NORMAL', foreground="black")
    
    def log(self, message: str, level: str = "NORMAL", with_time: bool = True):
        """
        Add a log message.
        
        Args:
            message: Message to log
            level: Log level (ERROR, SUCCESS, WARNING, INFO, DEBUG, NORMAL)
            with_time: Whether to include timestamp
        """
        self.configure(state='normal')
        
        if with_time:
            timestamp = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
            line = f"{timestamp} - {message}\n"
        else:
            line = f"{message}\n"
        
        self.insert("end", line, level.upper())
        self.see("end")
        self.configure(state='disabled')
    
    def log_error(self, message: str, with_time: bool = True):
        """Log an error message"""
        self.log(message, "ERROR", with_time)
    
    def log_success(self, message: str, with_time: bool = True):
        """Log a success message"""
        self.log(message, "SUCCESS", with_time)
    
    def log_warning(self, message: str, with_time: bool = True):
        """Log a warning message"""
        self.log(message, "WARNING", with_time)
    
    def log_info(self, message: str, with_time: bool = True):
        """Log an info message"""
        self.log(message, "INFO", with_time)
    
    def clear(self):
        """Clear all log messages"""
        self.configure(state='normal')
        self.delete("1.0", "end")
        self.configure(state='disabled')
