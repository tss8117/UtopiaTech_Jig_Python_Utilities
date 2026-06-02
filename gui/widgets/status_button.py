# ============================================================================
# JIG ONE v1.1 - Status Button Widget
# ============================================================================

import customtkinter as ctk
from typing import Optional

from config.settings import (
    PASS_COLOR,
    FAIL_COLOR,
    PENDING_COLOR,
    DEFAULT_GRAY,
    DEFAULT_COLOR,
)


class StatusButton(ctk.CTkButton):
    """
    A button that displays test status with color coding.
    
    Colors:
    - Grey: Not tested
    - Yellow: Pending/Testing
    - Green: Passed
    - Red: Failed
    """
    
    def __init__(
        self,
        master,
        text: str,
        width: int = 115,
        height: int = 45,
        font: tuple = ("Calibri", 17),
        **kwargs
    ):
        super().__init__(
            master,
            text=text,
            width=width,
            height=height,
            font=font,
            fg_color=DEFAULT_GRAY,
            text_color="white",
            hover=False,
            **kwargs
        )
        
        self._status: str = "not_tested"
    
    def set_status(self, status: str):
        """
        Set the button status.
        
        Args:
            status: 'not_tested', 'pending', 'pass', 'fail'
        """
        self._status = status
        
        if status == "pending":
            self.configure(fg_color=PENDING_COLOR, text_color="black")
        elif status == "pass":
            self.configure(fg_color=PASS_COLOR, text_color="black")
        elif status == "fail":
            self.configure(fg_color=FAIL_COLOR, text_color="white")
        else:  # not_tested or default
            self.configure(fg_color=DEFAULT_GRAY, text_color="white")
    
    def set_from_result(self, passed: bool):
        """
        Set status from test result.
        
        Args:
            passed: True for pass, False for fail
        """
        self.set_status("pass" if passed else "fail")
    
    def reset(self):
        """Reset to not tested state"""
        self.set_status("not_tested")
    
    def set_pending(self):
        """Set to pending state"""
        self.set_status("pending")
    
    @property
    def status(self) -> str:
        """Get current status"""
        return self._status


class StatusIndicator(ctk.CTkFrame):
    """
    A simple status indicator (colored circle/square).
    """
    
    def __init__(
        self,
        master,
        size: int = 20,
        **kwargs
    ):
        super().__init__(
            master,
            width=size,
            height=size,
            fg_color=DEFAULT_GRAY,
            corner_radius=size // 2,
            **kwargs
        )
        
        self._status = "not_tested"
    
    def set_status(self, status: str):
        """Set indicator status"""
        self._status = status
        
        if status == "pending":
            self.configure(fg_color=PENDING_COLOR)
        elif status == "pass":
            self.configure(fg_color=PASS_COLOR)
        elif status == "fail":
            self.configure(fg_color=FAIL_COLOR)
        else:
            self.configure(fg_color=DEFAULT_GRAY)
