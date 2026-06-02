# ============================================================================
# JIG ONE v1.1 - Results Frame (Dynamic GUI from JSON)
# ============================================================================

import customtkinter as ctk
from typing import Dict, List, Optional

from models.product_config import ProductConfig
from models import TestResultsManager, TestResult
from gui.widgets.status_button import StatusButton


class ResultsFrame(ctk.CTkFrame):
    """
    Dynamic test results display frame with scrolling support.
    
    Builds GUI elements from product configuration JSON.
    Automatically adapts when product config changes.
    """
    
    def __init__(
        self,
        master,
        product_config: ProductConfig,
        results_manager: TestResultsManager,
        **kwargs
    ):
        super().__init__(master, **kwargs)
        
        self.product_config = product_config
        self.results_manager = results_manager
        
        # Widget storage
        self.peripheral_buttons: Dict[str, StatusButton] = {}
        self.digital_input_buttons: Dict[str, StatusButton] = {}
        self.relay_buttons: Dict[str, StatusButton] = {}
        self.additional_buttons: Dict[str, StatusButton] = {}
        
        # Create scrollable container
        self._create_scrollable_frame()
        
        # Build UI
        self._build_ui()
    
    def _create_scrollable_frame(self):
        """Create a scrollable frame for the content"""
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )
        self.scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    def _build_ui(self):
        """Build the dynamic UI from product config"""
        # Use pack layout for sections, grid for buttons within sections
        
        # =====================================================================
        # PERIPHERALS SECTION
        # =====================================================================
        peripheral_names = self.product_config.get_peripheral_names()
        if peripheral_names:
            # Section header
            peri_header = ctk.CTkLabel(
                self.scrollable_frame, 
                text="Peripherals", 
                font=("Calibri", 18, "bold")
            )
            peri_header.pack(pady=(10, 5))
            
            # Button container
            peri_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
            peri_frame.pack(fill="x", padx=10, pady=5)
            
            # Configure grid columns to expand
            for i in range(len(peripheral_names)):
                peri_frame.grid_columnconfigure(i, weight=1)
            
            for i, name in enumerate(peripheral_names):
                btn = StatusButton(peri_frame, text=name, width=120, height=40)
                btn.grid(row=0, column=i, padx=5, pady=5, sticky="ew")
                self.peripheral_buttons[name] = btn
                
                # Link to results manager
                if name in self.results_manager.peripherals:
                    self.results_manager.peripherals[name].gui_element = btn
        
        # =====================================================================
        # DIGITAL INPUTS SECTION
        # =====================================================================
        dig_input_names = self.product_config.get_digital_input_names()
        if dig_input_names:
            # Section header
            dig_header = ctk.CTkLabel(
                self.scrollable_frame, 
                text="Digital Inputs", 
                font=("Calibri", 18, "bold")
            )
            dig_header.pack(pady=(15, 5))
            
            # Button container
            dig_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
            dig_frame.pack(fill="x", padx=10, pady=5)
            
            # 12 items per row
            items_per_row = 12
            num_rows = (len(dig_input_names) + items_per_row - 1) // items_per_row
            
            # Configure columns
            for i in range(items_per_row):
                dig_frame.grid_columnconfigure(i, weight=1)
            
            for i, name in enumerate(dig_input_names):
                row = i // items_per_row
                col = i % items_per_row
                
                btn = StatusButton(dig_frame, text=name, width=100, height=40)
                btn.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
                self.digital_input_buttons[name] = btn
                
                # Link to results manager
                if name in self.results_manager.digital_inputs:
                    self.results_manager.digital_inputs[name].gui_element = btn
        
        # =====================================================================
        # RELAYS SECTION
        # =====================================================================
        relay_names = self.product_config.get_relay_names()
        if relay_names:
            # Section header
            relay_header = ctk.CTkLabel(
                self.scrollable_frame, 
                text="Relays", 
                font=("Calibri", 18, "bold")
            )
            relay_header.pack(pady=(15, 5))
            
            # Button container
            relay_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
            relay_frame.pack(fill="x", padx=10, pady=5)
            
            # Configure columns for 12 relays
            for i in range(len(relay_names)):
                relay_frame.grid_columnconfigure(i, weight=1)
            
            for i, name in enumerate(relay_names):
                btn = StatusButton(relay_frame, text=name, width=100, height=40)
                btn.grid(row=0, column=i, padx=3, pady=3, sticky="ew")
                self.relay_buttons[name] = btn
                
                # Link to results manager
                if name in self.results_manager.relays:
                    self.results_manager.relays[name].gui_element = btn
        
        # =====================================================================
        # ADDITIONAL TESTS SECTION (Placeholder for future expansion)
        # =====================================================================
        additional_tests = self.product_config.get_additional_tests()
        enabled_additional = [t for t in additional_tests if t.get("enabled", False)]
        
        if enabled_additional:
            # Section header
            add_header = ctk.CTkLabel(
                self.scrollable_frame, 
                text="Additional Tests", 
                font=("Calibri", 18, "bold")
            )
            add_header.pack(pady=(15, 5))
            
            # Button container
            add_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
            add_frame.pack(fill="x", padx=10, pady=5)
            
            for i in range(len(enabled_additional)):
                add_frame.grid_columnconfigure(i, weight=1)
            
            for i, test in enumerate(enabled_additional):
                name = test["name"]
                btn = StatusButton(add_frame, text=name, width=120, height=40)
                btn.grid(row=0, column=i, padx=5, pady=5, sticky="ew")
                self.additional_buttons[name] = btn
                
                # Link to results manager
                if name in self.results_manager.additional_tests:
                    self.results_manager.additional_tests[name].gui_element = btn
    
    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================
    
    def update_from_results(self):
        """Update all buttons from results manager"""
        # Peripherals
        for name, item in self.results_manager.peripherals.items():
            if name in self.peripheral_buttons:
                btn = self.peripheral_buttons[name]
                if item.result == TestResult.PASS:
                    btn.set_status("pass")
                elif item.result == TestResult.FAIL:
                    btn.set_status("fail")
                elif item.result == TestResult.PENDING:
                    btn.set_status("pending")
                else:
                    btn.set_status("not_tested")
        
        # Digital Inputs
        for name, item in self.results_manager.digital_inputs.items():
            if name in self.digital_input_buttons:
                btn = self.digital_input_buttons[name]
                if item.result == TestResult.PASS:
                    btn.set_status("pass")
                elif item.result == TestResult.FAIL:
                    btn.set_status("fail")
                elif item.result == TestResult.PENDING:
                    btn.set_status("pending")
                else:
                    btn.set_status("not_tested")
        
        # Relays
        for name, item in self.results_manager.relays.items():
            if name in self.relay_buttons:
                btn = self.relay_buttons[name]
                if item.result == TestResult.PASS:
                    btn.set_status("pass")
                elif item.result == TestResult.FAIL:
                    btn.set_status("fail")
                elif item.result == TestResult.PENDING:
                    btn.set_status("pending")
                else:
                    btn.set_status("not_tested")
        
        # Additional
        for name, item in self.results_manager.additional_tests.items():
            if name in self.additional_buttons:
                btn = self.additional_buttons[name]
                if item.result == TestResult.PASS:
                    btn.set_status("pass")
                elif item.result == TestResult.FAIL:
                    btn.set_status("fail")
                elif item.result == TestResult.PENDING:
                    btn.set_status("pending")
                else:
                    btn.set_status("not_tested")
    
    def set_all_pending(self):
        """Set all buttons to pending status"""
        for btn in self.peripheral_buttons.values():
            btn.set_pending()
        for btn in self.digital_input_buttons.values():
            btn.set_pending()
        for btn in self.relay_buttons.values():
            btn.set_pending()
        for btn in self.additional_buttons.values():
            btn.set_pending()
    
    def reset_all(self):
        """Reset all buttons to not tested"""
        for btn in self.peripheral_buttons.values():
            btn.reset()
        for btn in self.digital_input_buttons.values():
            btn.reset()
        for btn in self.relay_buttons.values():
            btn.reset()
        for btn in self.additional_buttons.values():
            btn.reset()
    
    def set_category_pending(self, category: str):
        """Set a specific category to pending"""
        if category == "PERIPHERALS":
            for btn in self.peripheral_buttons.values():
                btn.set_pending()
        elif category == "DIGITAL_INPUTS":
            for btn in self.digital_input_buttons.values():
                btn.set_pending()
        elif category == "RELAYS":
            for btn in self.relay_buttons.values():
                btn.set_pending()
        elif category == "ADDITIONAL":
            for btn in self.additional_buttons.values():
                btn.set_pending()
    
    def get_test_counts(self) -> Dict[str, int]:
        """Get counts of tests by status"""
        counts = {"total": 0, "pass": 0, "fail": 0, "pending": 0, "not_tested": 0}
        
        all_buttons = (
            list(self.peripheral_buttons.values()) +
            list(self.digital_input_buttons.values()) +
            list(self.relay_buttons.values()) +
            list(self.additional_buttons.values())
        )
        
        for btn in all_buttons:
            counts["total"] += 1
            if btn.status == "pass":
                counts["pass"] += 1
            elif btn.status == "fail":
                counts["fail"] += 1
            elif btn.status == "pending":
                counts["pending"] += 1
            else:
                counts["not_tested"] += 1
        
        return counts
