from datetime import datetime


def format_test_response(
    product,
    serial_no,
    mac_id,
    mode,
    attempt,
    overall_status,
    clock_frequency_hz=None,
    peripherals=None,
    digital_inputs=None,
    relays=None,
    failed_areas=None,
    log_file=None
):
    return {
        "product": product,
        "serial_no": serial_no,
        "mac_id": mac_id,
        "mode": mode,
        "attempt": attempt,
        "overall_status": overall_status,
        "clock_frequency_hz": clock_frequency_hz,
        "peripherals": peripherals or [],
        "digital_inputs": digital_inputs or [],
        "relays": relays or [],
        "failed_areas": failed_areas or [],
        "log_file": log_file,
        "completed_at": datetime.now().isoformat()
    }