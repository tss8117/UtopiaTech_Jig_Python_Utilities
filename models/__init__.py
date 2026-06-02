# ============================================================================
# JIG ONE v1.2 - Models Package
# ============================================================================

from .product_config import (
    ProductConfig,
    PeripheralConfig,
    DigitalInputConfig,
    RelayConfig,
    ClockConfig,
    FirmwarePathConfig,
    list_available_products,
    get_product_info,
)

from .test_results import (
    TestResult,
    TestItem,
    TestAttempt,
    TestResultsManager,
)

__all__ = [
    'ProductConfig',
    'PeripheralConfig',
    'DigitalInputConfig',
    'RelayConfig',
    'ClockConfig',
    'FirmwarePathConfig',
    'list_available_products',
    'get_product_info',
    'TestResult',
    'TestItem',
    'TestAttempt',
    'TestResultsManager',
]
