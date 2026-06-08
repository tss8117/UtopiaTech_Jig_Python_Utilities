import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

import serial


DEFAULT_BAUDRATE = 115200
DEFAULT_TIMEOUT_SECONDS = 10


class HardwareCommandError(Exception):
    pass


def _open_serial(port: str, baudrate: int = DEFAULT_BAUDRATE) -> serial.Serial:
    if not port:
        raise HardwareCommandError("Serial port is required")

    try:
        return serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=0.5,
            write_timeout=2
        )
    except Exception as ex:
        raise HardwareCommandError(f"Failed to open serial port {port}: {ex}")


def _send_json_command(
    port: str,
    command: Dict[str, Any],
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
) -> Dict[str, Any]:
    """
    Real STM32 command exchange.

    Expected STM32 firmware contract:
    - Pi/Node-RED sends one JSON command line over USB CDC serial.
    - STM32 executes the command.
    - STM32 returns one JSON response line.

    Example TX:
    {"cmd":"POWER_ON","params":{"soft_start":true}}

    Example RX:
    {"ok":true,"cmd":"POWER_ON","value":{"vbus":12.04,"current_ma":180}}
    """

    ser: Optional[serial.Serial] = None

    try:
        ser = _open_serial(port)

        payload = json.dumps(command) + "\n"
        ser.write(payload.encode("utf-8"))
        ser.flush()

        deadline = time.time() + timeout_seconds
        response_bytes = b""

        while time.time() < deadline:
            line = ser.readline()

            if not line:
                continue

            response_bytes += line

            try:
                response_text = response_bytes.decode("utf-8").strip()
                return json.loads(response_text)
            except json.JSONDecodeError:
                continue

        raise HardwareCommandError(
            f"No valid JSON response received from STM32 within {timeout_seconds} seconds"
        )

    finally:
        if ser and ser.is_open:
            ser.close()


def _build_step_result(
    step_id: str,
    module: str,
    test_name: str,
    command_response: Dict[str, Any],
    expected: str
) -> Dict[str, Any]:
    ok = bool(command_response.get("ok", False))

    return {
        "step_id": step_id,
        "module": module,
        "test_name": test_name,
        "status": "PASS" if ok else "FAIL",
        "measured_value": command_response.get("value", {}),
        "expected": expected,
        "raw_response": command_response,
        "timestamp": datetime.now().isoformat()
    }


def power_on_dut(port: str, product: str) -> Dict[str, Any]:
    response = _send_json_command(
        port,
        {
            "cmd": "POWER_ON",
            "product": product,
            "params": {
                "soft_start": True,
                "measure_current": True
            }
        }
    )

    return _build_step_result(
        step_id="POWER_ON",
        module="Power Control",
        test_name="Power On DUT",
        command_response=response,
        expected="DUT 12V power should turn on and current should be within safe limit"
    )


def measure_voltage(port: str, product: str, channel: str, minimum: float, maximum: float) -> Dict[str, Any]:
    response = _send_json_command(
        port,
        {
            "cmd": "MEASURE_VOLTAGE",
            "product": product,
            "params": {
                "channel": channel,
                "min": minimum,
                "max": maximum
            }
        }
    )

    # If STM32 returns only value, Python can still evaluate.
    if "ok" not in response and "value" in response:
        value = response["value"].get("voltage")
        response["ok"] = value is not None and minimum <= float(value) <= maximum

    return _build_step_result(
        step_id="MEASURE_VOLTAGE",
        module="Power Control",
        test_name=f"Measure Voltage - {channel}",
        command_response=response,
        expected=f"{channel} voltage should be between {minimum}V and {maximum}V"
    )


def check_relay(port: str, product: str, relay_name: str, expected_state: str) -> Dict[str, Any]:
    response = _send_json_command(
        port,
        {
            "cmd": "CHECK_RELAY",
            "product": product,
            "params": {
                "relay_name": relay_name,
                "expected_state": expected_state
            }
        }
    )

    return _build_step_result(
        step_id="CHECK_RELAY",
        module="Relay / Control",
        test_name=f"Check Relay - {relay_name}",
        command_response=response,
        expected=f"{relay_name} should switch to {expected_state}"
    )


def measure_frequency(port: str, product: str, target_hz: float, tolerance_hz: float) -> Dict[str, Any]:
    response = _send_json_command(
        port,
        {
            "cmd": "MEASURE_FREQUENCY",
            "product": product,
            "params": {
                "target_hz": target_hz,
                "tolerance_hz": tolerance_hz
            }
        },
        timeout_seconds=20
    )

    if "ok" not in response and "value" in response:
        freq = response["value"].get("frequency_hz")
        response["ok"] = freq is not None and abs(float(freq) - target_hz) <= tolerance_hz

    return _build_step_result(
        step_id="MEASURE_FREQUENCY",
        module="Frequency Measurement",
        test_name="Measure RTC Crystal",
        command_response=response,
        expected=f"Frequency should be {target_hz}Hz ± {tolerance_hz}Hz"
    )


def rs485_transaction(port: str, product: str, request: str, expected_reply: str) -> Dict[str, Any]:
    response = _send_json_command(
        port,
        {
            "cmd": "RS485_TRANSACTION",
            "product": product,
            "params": {
                "request": request,
                "expected_reply": expected_reply
            }
        }
    )

    return _build_step_result(
        step_id="RS485_TRANSACTION",
        module="Communication",
        test_name="RS485 Transaction",
        command_response=response,
        expected=f"DUT should respond with {expected_reply}"
    )