from datetime import datetime

from node_red_bridge.response_formatter import format_test_response
from core.serial_handler import SerialHandler


def run_test_cycle(product, serial_no, mac_id, mode="user"):
    """
    Simulation mode for Node-RED integration.
    No real jig board or Raspberry Pi required.
    """

    import random
    from datetime import datetime

    simulation_mode = mode

    if simulation_mode == "mock-fail":
        overall_status = "FAIL"

        peripherals = [
            {"name": "EEPROM", "status": "PASS"},
            {"name": "RTC", "status": "FAIL"},
            {"name": "RS485 Communication", "status": "PASS"}
        ]

        digital_inputs = [
            {"name": "Zone 1", "status": "PASS"},
            {"name": "Zone 2", "status": "FAIL"},
            {"name": "Zone 3", "status": "PASS"},
            {"name": "Zone 4", "status": "PASS"}
        ]

        relays = [
            {"name": "Relay 1", "status": "PASS"},
            {"name": "Relay 2", "status": "FAIL"}
        ]

        failed_areas = ["RTC", "Zone 2", "Relay 2"]

    elif simulation_mode == "mock-random":
        peripherals = [
            {"name": "EEPROM", "status": random.choice(["PASS", "PASS", "FAIL"])},
            {"name": "RTC", "status": random.choice(["PASS", "PASS", "FAIL"])},
            {"name": "RS485 Communication", "status": random.choice(["PASS", "PASS", "FAIL"])}
        ]

        digital_inputs = [
            {"name": f"Zone {i}", "status": random.choice(["PASS", "PASS", "FAIL"])}
            for i in range(1, 5)
        ]

        relays = [
            {"name": f"Relay {i}", "status": random.choice(["PASS", "PASS", "FAIL"])}
            for i in range(1, 3)
        ]

        all_tests = peripherals + digital_inputs + relays
        failed_areas = [item["name"] for item in all_tests if item["status"] == "FAIL"]
        overall_status = "FAIL" if failed_areas else "PASS"

    else:
        overall_status = "PASS"

        peripherals = [
            {"name": "EEPROM", "status": "PASS"},
            {"name": "RTC", "status": "PASS"},
            {"name": "RS485 Communication", "status": "PASS"}
        ]

        digital_inputs = [
            {"name": "Zone 1", "status": "PASS"},
            {"name": "Zone 2", "status": "PASS"},
            {"name": "Zone 3", "status": "PASS"},
            {"name": "Zone 4", "status": "PASS"}
        ]

        relays = [
            {"name": "Relay 1", "status": "PASS"},
            {"name": "Relay 2", "status": "PASS"}
        ]

        failed_areas = []

    return format_test_response(
        product=product,
        serial_no=serial_no,
        mac_id=mac_id,
        mode=mode,
        attempt=1,
        overall_status=overall_status,
        clock_frequency_hz=32768,
        peripherals=peripherals,
        digital_inputs=digital_inputs,
        relays=relays,
        failed_areas=failed_areas,
        log_file=f"Offline_Logs/{datetime.now().strftime('%Y-%m')}/{product}_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    )


def program_firmware(product, firmware_type="test_code"):
    return {
        "product": product,
        "firmware_type": firmware_type,
        "status": "PASS",
        "message": "Firmware programming completed successfully"
    }


def list_serial_ports():
    ports = SerialHandler.list_ports()

    return [
        {
            "device": p.device,
            "product": p.product,
            "description": p.description,
            "display_name": p.display_name
        }
        for p in ports
    ]