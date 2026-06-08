#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from node_red_bridge.product_service import list_products, get_product
from node_red_bridge.test_runner import run_test_cycle, program_firmware, list_serial_ports
from node_red_bridge.hardware_commands import (
    power_on_dut,
    measure_voltage,
    check_relay,
    measure_frequency,
    rs485_transaction,
)
def success(data):
    print(json.dumps({
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "data": data
    }, indent=2))


def failure(message, details=None):
    print(json.dumps({
        "success": False,
        "timestamp": datetime.now().isoformat(),
        "error": message,
        "details": details or {}
    }, indent=2))
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Node-RED bridge for JIG ONE")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list-products")
    subparsers.add_parser("list-serial-ports")

    get_product_parser = subparsers.add_parser("get-product")
    get_product_parser.add_argument("--product", required=True)

    run_test_parser = subparsers.add_parser("run-test")
    run_test_parser.add_argument("--product", required=True)
    run_test_parser.add_argument("--serial", required=True)
    run_test_parser.add_argument("--mac", required=True)
    run_test_parser.add_argument(
    "--mode",
    choices=["user", "developer", "mock-pass", "mock-fail", "mock-random"],
    default="mock-pass"
    )

    program_parser = subparsers.add_parser("program-firmware")
    program_parser.add_argument("--product", required=True)
    program_parser.add_argument(
        "--firmware-type",
        choices=["bootloader", "test_code", "final_firmware"],
        default="test_code"
    )

    power_parser = subparsers.add_parser("power-on")
    power_parser.add_argument("--product", required=True)
    power_parser.add_argument("--port", required=True)

    voltage_parser = subparsers.add_parser("measure-voltage")
    voltage_parser.add_argument("--product", required=True)
    voltage_parser.add_argument("--port", required=True)
    voltage_parser.add_argument("--channel", required=True)
    voltage_parser.add_argument("--min", type=float, required=True)
    voltage_parser.add_argument("--max", type=float, required=True)

    relay_parser = subparsers.add_parser("check-relay")
    relay_parser.add_argument("--product", required=True)
    relay_parser.add_argument("--port", required=True)
    relay_parser.add_argument("--relay", required=True)
    relay_parser.add_argument("--expected-state", required=True)

    freq_parser = subparsers.add_parser("measure-frequency")
    freq_parser.add_argument("--product", required=True)
    freq_parser.add_argument("--port", required=True)
    freq_parser.add_argument("--target-hz", type=float, required=True)
    freq_parser.add_argument("--tolerance-hz", type=float, required=True)

    rs485_parser = subparsers.add_parser("rs485-transaction")
    rs485_parser.add_argument("--product", required=True)
    rs485_parser.add_argument("--port", required=True)
    rs485_parser.add_argument("--request", required=True)
    rs485_parser.add_argument("--expected-reply", required=True)

    args = parser.parse_args()

    try:
        if args.command == "list-products":
            success(list_products())

        elif args.command == "list-serial-ports":
            success(list_serial_ports())

        elif args.command == "get-product":
            success(get_product(args.product))

        elif args.command == "run-test":
            result = run_test_cycle(
                product=args.product,
                serial_no=args.serial,
                mac_id=args.mac,
                mode=args.mode
            )
            success(result)

        elif args.command == "program-firmware":
            result = program_firmware(
                product=args.product,
                firmware_type=args.firmware_type
            )
            success(result)
        
        elif args.command == "power-on":
            success(power_on_dut(args.port, args.product))

        elif args.command == "measure-voltage":
            success(measure_voltage(args.port, args.product, args.channel, args.min, args.max))

        elif args.command == "check-relay":
            success(check_relay(args.port, args.product, args.relay, args.expected_state))

        elif args.command == "measure-frequency":
            success(measure_frequency(args.port, args.product, args.target_hz, args.tolerance_hz))

        elif args.command == "rs485-transaction":
            success(rs485_transaction(args.port, args.product, args.request, args.expected_reply))

        else:
            failure("Invalid command")

    except Exception as ex:
        failure(str(ex), {"type": type(ex).__name__})


if __name__ == "__main__":
    main()