# ============================================================================
# JIG ONE v1.1 - Product Configuration Model
# ============================================================================

import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from config.settings import (
    PRODUCTS_DIR,
    CONFIG_TEMPLATE_DIR,
    get_product_config_path,
    BASE_DIR,
)


@dataclass
class PeripheralConfig:
    """Configuration for a single peripheral test"""
    name: str
    bit_position: int
    critical: bool = False  # Exists but not implemented per user decision
    enabled: bool = True


@dataclass
class DigitalInputConfig:
    """Configuration for digital inputs"""
    zones_count: int = 36
    zones_name_format: str = "Zone {n}"
    additional: List[Dict[str, Any]] = field(default_factory=list)


# @dataclass
# class RelayConfig:
#     """Configuration for relays"""
#     count: int = 12
#     name_format: str = "Relay {n}"

@dataclass
class RelayConfig:
    """Configuration for relays"""
    count: int = 12
    name_format: str = "Relay {n}"
    silkscreen_refs: List[str] = field(default_factory=list)

@dataclass
class ClockConfig:
    """Configuration for clock measurement"""
    nominal_hz: int = 32768
    min_hz: int = 32000
    max_hz: int = 32900


@dataclass
class FirmwarePathConfig:
    """Configuration for a firmware file"""
    path: str = ""
    openocd_template: str = ""


class ProductConfig:
    """
    Loads and manages product test configuration from JSON.
    Supports multiple product configurations via JSON files.
    """
    
    DEFAULT_CONFIG = {
        "product_name": "ESS Main Board",
        "product_code": "ESS_MAIN",
        "version": "1.0",
        "peripherals": [
            {"name": "EEPROM", "bit_position": 0, "critical": False, "enabled": True},
            {"name": "RTC", "bit_position": 1, "critical": False, "enabled": True},
            {"name": "RTC Battery", "bit_position": 2, "critical": False, "enabled": True},
            {"name": "Battery Voltage", "bit_position": 3, "critical": False, "enabled": True},
            {"name": "Temp. Sensor", "bit_position": 4, "critical": False, "enabled": True},
            {"name": "Smoke Zone", "bit_position": 5, "critical": False, "enabled": True},
            {"name": "GPIO", "bit_position": 6, "critical": False, "enabled": True},
            {"name": "W5500", "bit_position": 7, "critical": False, "enabled": True},
            {"name": "Clock Frequency", "bit_position": 8, "critical": False, "enabled": True},
        ],
        "digital_inputs": {
            "zones": {"count": 36, "name_format": "Zone {n}"},
            "additional": [
                {"name": "ZONE 1 DET", "index": 36, "enabled": True},
                {"name": "ZONE 2 DET", "index": 37, "enabled": True},
                {"name": "ZONE 3 DET", "index": 38, "enabled": True},
                {"name": "Analog 3V3", "index": 39, "enabled": True},
                {"name": "Silence Key", "index": 40, "enabled": True},
                {"name": "ADE IRQ", "index": 41, "enabled": True},
                {"name": "AC DETECT", "index": 42, "enabled": True},
            ]
        },
        "relays": {"count": 12, "name_format": "Relay {n}"},
        "clock": {"nominal_hz": 32768, "min_hz": 32000, "max_hz": 32900},
        "firmware": {
            "bootloader": {
                "path": "",
                "openocd_template": "Config_Template/boot_template_openocd.cfg"
            },
            "test_code": {
                "path": "",
                "openocd_template": "Config_Template/template_openocd.cfg"
            },
            "final_firmware": {
                "path": "",
                "openocd_template": "Config_Template/template_openocd.cfg"
            }
        },
        "additional_tests": [
            # Placeholder for future tests - GUI will dynamically add these
            # {"name": "Calibration", "bit_position": 0, "enabled": False},
            # {"name": "Audio Test", "bit_position": 1, "enabled": False},
        ]
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize ProductConfig.
        
        Args:
            config_path: Path to JSON config file. If None, uses selected product config.
        """
        self.config_path = config_path or get_product_config_path()
        self.config = self._load_config()
        
    def _load_config(self) -> dict:
        """Load configuration from JSON file"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    loaded = json.load(f)
                    print(f"[CONFIG] Loaded product config: {self.config_path}")
                    return self._merge_with_defaults(loaded)
            except Exception as e:
                print(f"[CONFIG] Error loading {self.config_path}: {e}")
                print("[CONFIG] Using default configuration")
        else:
            print(f"[CONFIG] Config not found: {self.config_path}")
            self._save_default_config()
        
        return self.DEFAULT_CONFIG.copy()
    
    def _merge_with_defaults(self, loaded: dict) -> dict:
        """Merge loaded config with defaults to ensure all fields exist"""
        merged = self.DEFAULT_CONFIG.copy()
        
        # Deep merge
        for key, value in loaded.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key].update(value)
            else:
                merged[key] = value
        
        return merged
    
    def _save_default_config(self):
        """Save default configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.DEFAULT_CONFIG, f, indent=4)
            print(f"[CONFIG] Created default config: {self.config_path}")
        except Exception as e:
            print(f"[CONFIG] Error saving default config: {e}")
    
    def save(self):
        """Save current configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            print(f"[CONFIG] Saved config: {self.config_path}")
        except Exception as e:
            print(f"[CONFIG] Error saving config: {e}")
    
    # ========================================================================
    # GETTERS
    # ========================================================================
    
    @property
    def product_name(self) -> str:
        return self.config.get("product_name", "Unknown Product")
    
    @property
    def product_code(self) -> str:
        return self.config.get("product_code", "UNKNOWN")
    
    def get_peripheral_configs(self) -> List[PeripheralConfig]:
        """Get list of peripheral configurations"""
        peripherals = []
        for p in self.config.get("peripherals", []):
            if p.get("enabled", True):
                peripherals.append(PeripheralConfig(
                    name=p["name"],
                    bit_position=p["bit_position"],
                    critical=p.get("critical", False),
                    enabled=p.get("enabled", True)
                ))
        return peripherals
    
    def get_peripheral_names(self) -> List[str]:
        """Get list of enabled peripheral names"""
        return [p.name for p in self.get_peripheral_configs()]
    
    def get_digital_input_names(self) -> List[str]:
        """Get list of all digital input names (zones + additional)"""
        names = []
        dig_config = self.config.get("digital_inputs", {})
        
        # Zones
        zones = dig_config.get("zones", {})
        zone_count = zones.get("count", 36)
        name_format = zones.get("name_format", "Zone {n}")
        
        for i in range(1, zone_count + 1):
            names.append(name_format.format(n=i))
        
        # Additional inputs
        for item in dig_config.get("additional", []):
            if item.get("enabled", True):
                names.append(item["name"])
        
        return names
    
    def get_zone_count(self) -> int:
        """Get number of zones"""
        return self.config.get("digital_inputs", {}).get("zones", {}).get("count", 36)
    
    def get_additional_inputs(self) -> List[Dict[str, Any]]:
        """Get additional digital input configurations"""
        return self.config.get("digital_inputs", {}).get("additional", [])
    
    # def get_relay_names(self) -> List[str]:
    #     """Get list of relay names"""
    #     relay_config = self.config.get("relays", {})
    #     count = relay_config.get("count", 12)
    #     name_format = relay_config.get("name_format", "Relay {n}")
    #     return [name_format.format(n=i) for i in range(1, count + 1)]

    def get_relay_names(self) -> List[str]:
        """Get list of relay names with optional silkscreen references"""
        relay_config = self.config.get("relays", {})
        
        # Check if using new explicit items format
        if "items" in relay_config:
            names = []
            for item in relay_config["items"]:
                name = item.get("name", f"Relay {item['index']}")
                silkscreen = item.get("silkscreen", "")
                if silkscreen:
                    names.append(f"{name} ({silkscreen})")
                else:
                    names.append(name)
            return names
        
        # Legacy format with count and name_format
        count = relay_config.get("count", 12)
        name_format = relay_config.get("name_format", "Relay {n}")
        silkscreen_refs = relay_config.get("silkscreen_refs", [])
        
        names = []
        for i in range(1, count + 1):
            base_name = name_format.format(n=i)
            # Add silkscreen reference if available
            if i - 1 < len(silkscreen_refs) and silkscreen_refs[i - 1]:
                names.append(f"{base_name} ({silkscreen_refs[i - 1]})")
            else:
                names.append(base_name)
        
        return names

    def get_relay_count(self) -> int:
        """Get number of relays"""
        return self.config.get("relays", {}).get("count", 12)
    
    def get_clock_config(self) -> ClockConfig:
        """Get clock measurement configuration"""
        clock = self.config.get("clock", {})
        return ClockConfig(
            nominal_hz=clock.get("nominal_hz", 32768),
            min_hz=clock.get("min_hz", 32000),
            max_hz=clock.get("max_hz", 32900)
        )
    
    def get_firmware_paths(self) -> Dict[str, FirmwarePathConfig]:
        """Get firmware path configurations"""
        firmware = self.config.get("firmware", {})
        return {
            "bootloader": FirmwarePathConfig(
                path=firmware.get("bootloader", {}).get("path", ""),
                openocd_template=firmware.get("bootloader", {}).get(
                    "openocd_template", "Config_Template/boot_template_openocd.cfg"
                )
            ),
            "test_code": FirmwarePathConfig(
                path=firmware.get("test_code", {}).get("path", ""),
                openocd_template=firmware.get("test_code", {}).get(
                    "openocd_template", "Config_Template/template_openocd.cfg"
                )
            ),
            "final_firmware": FirmwarePathConfig(
                path=firmware.get("final_firmware", {}).get("path", ""),
                openocd_template=firmware.get("final_firmware", {}).get(
                    "openocd_template", "Config_Template/template_openocd.cfg"
                )
            )
        }
    
    def get_additional_tests(self) -> List[Dict[str, Any]]:
        """Get additional test configurations (placeholder for future expansion)"""
        return self.config.get("additional_tests", [])
    
    # ========================================================================
    # SETTERS
    # ========================================================================
    
    def save_firmware_path(self, firmware_type: str, path: str):
        """
        Save firmware path to config.
        
        Args:
            firmware_type: 'BOOTLOADER', 'TEST', or 'FINAL'
            path: Path to firmware file
        """
        if "firmware" not in self.config:
            self.config["firmware"] = {
                "bootloader": {"path": "", "openocd_template": "Config_Template/boot_template_openocd.cfg"},
                "test_code": {"path": "", "openocd_template": "Config_Template/template_openocd.cfg"},
                "final_firmware": {"path": "", "openocd_template": "Config_Template/template_openocd.cfg"}
            }
        
        type_map = {
            "BOOTLOADER": "bootloader",
            "TEST": "test_code",
            "FINAL": "final_firmware"
        }
        
        if firmware_type in type_map:
            key = type_map[firmware_type]
            if key not in self.config["firmware"]:
                self.config["firmware"][key] = {"path": "", "openocd_template": ""}
            self.config["firmware"][key]["path"] = path
            self.save()
            print(f"[CONFIG] Saved {firmware_type} path: {path}")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def list_available_products() -> List[str]:
    """List all available product configuration files"""
    products = []
    if os.path.exists(PRODUCTS_DIR):
        for f in os.listdir(PRODUCTS_DIR):
            if f.endswith('.json'):
                products.append(f)
    return products


def get_product_info(config_name: str) -> Optional[Dict[str, str]]:
    """Get basic info about a product config without fully loading it"""
    config_path = os.path.join(PRODUCTS_DIR, config_name)
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
                return {
                    "name": data.get("product_name", "Unknown"),
                    "code": data.get("product_code", "UNKNOWN"),
                    "version": data.get("version", "1.0")
                }
        except Exception:
            pass
    return None
