# ============================================================================
# JIG ONE v1.1 - Developer Controls Frame
# ============================================================================

import customtkinter as ctk
from tkinter import StringVar
from typing import Callable, Optional

from config.settings import (
    DEFAULT_COLOR,
    DEV_DEFAULT_SERIAL_NO,
    DEV_DEFAULT_MAC_ID,
    MAX_DEVELOPER_RETRIES,
)
from config.constants import TestCategory, RetestStrategy
from core.retest_manager import RetestManager


class DeveloperFrame(ctk.CTkFrame):
    """
    Developer mode controls frame.
    
    Provides manual control over:
    - Retry counts and strategies
    - Manual retest triggers
    - Debug information
    - Default values loading
    """
    
    # NEW __init__ signature
    def __init__(
        self,
        master,
        retest_manager: RetestManager,
        on_load_defaults=None,
        on_clear_ids=None,
        on_reset=None,
        on_show_summary=None,
        on_log=None,
        **kwargs
    ):
    # Remove these two lines from the body:
    # self._on_manual_retest = on_manual_retest
    # self._on_specific_retest = on_specific_retest
        super().__init__(master, **kwargs)
        
        self.retest_manager = retest_manager
        
        # Callbacks
        self._on_load_defaults = on_load_defaults
        self._on_clear_ids = on_clear_ids
        self._on_reset = on_reset
        self._on_manual_retest = on_manual_retest
        self._on_specific_retest = on_specific_retest
        self._on_show_summary = on_show_summary
        self._on_log = on_log
        
        # Variables
        self.retry_count_var = StringVar(value="3")
        self.strategy_var = StringVar(value="FAILED_ONLY")
        
        # Build UI
        self._build_ui()
    
    def _build_ui(self):
        """Build the developer controls UI"""
        
        # Row 0: Header and Load/Clear buttons
        ctk.CTkLabel(
            self,
            text="🔧 DEVELOPER CONTROLS",
            font=("Calibri", 16, "bold"),
            text_color="#FF6B6B"
        ).grid(row=0, column=0, columnspan=2, pady=5, padx=10, sticky="w")
        
        ctk.CTkButton(
            self, width=100, text='Load Defaults',
            command=self._load_defaults,
            font=("Calibri", 12),
            fg_color="#2E8B57", hover_color="#3CB371"
        ).grid(row=0, column=2, pady=5, padx=5)
        
        ctk.CTkButton(
            self, width=60, text='Clear',
            command=self._clear_ids,
            font=("Calibri", 12),
            fg_color="#555555", hover_color="#777777"
        ).grid(row=0, column=3, pady=5, padx=3)
        
        # Retry count
        ctk.CTkLabel(
            self, text="Retries:", font=("Calibri", 14)
        ).grid(row=0, column=4, pady=5, padx=5, sticky="e")
        
        retry_entry = ctk.CTkEntry(
            self, width=40, textvariable=self.retry_count_var,
            font=("Calibri", 14)
        )
        retry_entry.grid(row=0, column=5, pady=5, padx=5)
        retry_entry.bind('<FocusOut>', lambda e: self._update_settings())
        retry_entry.bind('<Return>', lambda e: self._update_settings())
        
        # Strategy
        ctk.CTkLabel(
            self, text="Strategy:", font=("Calibri", 14)
        ).grid(row=0, column=6, pady=5, padx=5, sticky="e")
        
        ctk.CTkComboBox(
            self, width=120, variable=self.strategy_var,
            values=["FULL_SEQUENCE", "FAILED_ONLY", "SPECIFIC_TEST"],
            font=("Calibri", 11), state="readonly",
            command=lambda x: self._update_settings()
        ).grid(row=0, column=7, pady=5, padx=5)
        
        # # Row 1: Retest buttons
        # ctk.CTkButton(
        #     self, width=90, text='Retry All',
        #     command=lambda: self._manual_retest(RetestStrategy.FULL_SEQUENCE),
        #     font=("Calibri", 13),
        #     fg_color="#8B0000", hover_color="#A52A2A"
        # ).grid(row=1, column=0, pady=5, padx=5)
        
        # ctk.CTkButton(
        #     self, width=90, text='Retry Failed',
        #     command=lambda: self._manual_retest(RetestStrategy.FAILED_ONLY),
        #     font=("Calibri", 13),
        #     fg_color="#8B0000", hover_color="#A52A2A"
        # ).grid(row=1, column=1, pady=5, padx=5)
        
        # ctk.CTkButton(
        #     self, width=80, text='Retry Peri.',
        #     command=lambda: self._specific_retest(TestCategory.PERIPHERALS),
        #     font=("Calibri", 12),
        #     fg_color='#555555', hover_color='#777777'
        # ).grid(row=1, column=2, pady=5, padx=3)
        
        # ctk.CTkButton(
        #     self, width=80, text='Retry Zones',
        #     command=lambda: self._specific_retest(TestCategory.DIGITAL_INPUTS),
        #     font=("Calibri", 12),
        #     fg_color='#555555', hover_color='#777777'
        # ).grid(row=1, column=3, pady=5, padx=3)
        
        # ctk.CTkButton(
        #     self, width=80, text='Retry Relays',
        #     command=lambda: self._specific_retest(TestCategory.RELAYS),
        #     font=("Calibri", 12),
        #     fg_color='#555555', hover_color='#777777'
        # ).grid(row=1, column=4, pady=5, padx=3)
        
        # ctk.CTkButton(
        #     self, width=80, text='Summary',
        #     command=self._show_summary,
        #     font=("Calibri", 12),
        #     fg_color='#333333', hover_color='#555555'
        # ).grid(row=1, column=5, pady=5, padx=3)
        
        # # Reset button
        # ctk.CTkButton(
        #     self, width=100, text='🔄 RESET',
        #     command=self._reset,
        #     font=("Calibri", 13, "bold"),
        #     fg_color="#FF4500", hover_color="#FF6347"
        # ).grid(row=1, column=6, columnspan=2, pady=5, padx=10)
        
        # Row 2: Status label
        # self._status_label = ctk.CTkLabel(
        #     self,
        #     text="Status: DEV | Attempt: 0/3 | Strategy: FAILED ONLY",
        #     font=("Calibri", 12),
        #     text_color="#AAAAAA"
        # )
        self._status_label.grid(row=2, column=0, columnspan=6, pady=2, padx=10, sticky="w")
        # NEW Row 1 (Summary + Reset only)
        ctk.CTkButton(
            self, width=80, text='Summary',
            command=self._show_summary,
            font=("Calibri", 12),
            fg_color='#333333', hover_color='#555555'
        ).grid(row=1, column=0, pady=5, padx=3)

        ctk.CTkButton(
            self, width=100, text='🔄 RESET',
            command=self._reset,
            font=("Calibri", 13, "bold"),
            fg_color="#FF4500", hover_color="#FF6347"
        ).grid(row=1, column=1, pady=5, padx=10)

    def _load_defaults(self):
        """Load default Serial No. and MAC ID"""
        if self._on_load_defaults:
            self._on_load_defaults()
        self._log(f"Loaded defaults: Serial={DEV_DEFAULT_SERIAL_NO}, MAC={DEV_DEFAULT_MAC_ID}", "INFO")
    
    def _clear_ids(self):
        """Clear Serial No. and MAC ID"""
        if self._on_clear_ids:
            self._on_clear_ids()
        self._log("Cleared Serial No. and MAC ID", "INFO")
    
    def _reset(self):
        """Reset utility to defaults"""
        if self._on_reset:
            self._on_reset()
        self._log("=== UTILITY RESET TO DEFAULTS ===", "SUCCESS")
    
    # def _manual_retest(self, strategy: RetestStrategy):
    #     """Trigger manual retest"""
    #     if self._on_manual_retest:
    #         self._on_manual_retest(strategy)
    #     self._log(f"Manual retest initiated: {strategy.name}", "INFO")
    
    # def _specific_retest(self, category: TestCategory):
    #     """Trigger retest for specific category"""
    #     if self._on_specific_retest:
    #         self._on_specific_retest(category)
    #     self._log(f"Manual retest initiated for: {category.name}", "INFO")
    
    def _show_summary(self):
        """Show test summary"""
        if self._on_show_summary:
            self._on_show_summary()
    
    def _update_settings(self):
        """Update retest manager settings from UI"""
        try:
            count = int(self.retry_count_var.get())
            count = max(1, min(count, MAX_DEVELOPER_RETRIES))
            self.retest_manager.set_developer_retries(count)
            self.retry_count_var.set(str(count))
        except ValueError:
            self.retry_count_var.set("3")
            self.retest_manager.set_developer_retries(3)
        
        strategy_map = {
            "FULL_SEQUENCE": RetestStrategy.FULL_SEQUENCE,
            "FAILED_ONLY": RetestStrategy.FAILED_ONLY,
            "SPECIFIC_TEST": RetestStrategy.SPECIFIC_TEST
        }
        strategy = strategy_map.get(self.strategy_var.get(), RetestStrategy.FAILED_ONLY)
        self.retest_manager.set_retest_strategy(strategy)
        
        self.update_status()
    
    def update_status(self):
        """Update status display"""
        status = self.retest_manager.get_status_string()
        self._status_label.configure(text=f"Status: {status}")
    
    def _log(self, message: str, level: str = "INFO"):
        """Log a message"""
        if self._on_log:
            self._on_log(message, level)
