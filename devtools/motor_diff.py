#!/usr/bin/env python3
"""Interactive Raspberry Pi motor PWM/differential tester.

Run this on the Raspberry Pi with:

    python3 devtools/motor_diff.py
    ^ if this doesn't work, `cp devtools/motor_diff.py mt.py`, run mt.py

The script uses physical BOARD pin numbers from src/config.py. It starts both
motors forward at 50% duty cycle, then lets you enter signed PWM values to test
left/right motor balance and direction.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import RPi.GPIO as GPIO

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import config

LEFT_PWM_PIN = config.PIN_ENA
LEFT_FORWARD_PIN = config.PIN_IN1
LEFT_BACKWARD_PIN = config.PIN_IN2

RIGHT_PWM_PIN = config.PIN_ENB
RIGHT_FORWARD_PIN = config.PIN_IN3
RIGHT_BACKWARD_PIN = config.PIN_IN4

DEFAULT_PWM_HZ = 1000
DEFAULT_BASE_DUTY = 50.0


def clamp_duty(value: float) -> float:
    return max(-100.0, min(100.0, value))


def parse_float(value: str, name: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {value!r}") from exc


def set_motor(pwm: GPIO.PWM, forward_pin: int, backward_pin: int, duty: float) -> None:
    duty = clamp_duty(duty)

    if duty > 0:
        GPIO.output(forward_pin, GPIO.HIGH)
        GPIO.output(backward_pin, GPIO.LOW)
    elif duty < 0:
        GPIO.output(forward_pin, GPIO.LOW)
        GPIO.output(backward_pin, GPIO.HIGH)
    else:
        GPIO.output(forward_pin, GPIO.LOW)
        GPIO.output(backward_pin, GPIO.LOW)

    pwm.ChangeDutyCycle(abs(duty))


def apply_speeds(left_pwm: GPIO.PWM, right_pwm: GPIO.PWM, left: float, right: float) -> None:
    set_motor(left_pwm, LEFT_FORWARD_PIN, LEFT_BACKWARD_PIN, left)
    set_motor(right_pwm, RIGHT_FORWARD_PIN, RIGHT_BACKWARD_PIN, right)
    print(f"Applied left={clamp_duty(left):.1f}% right={clamp_duty(right):.1f}%")


def print_help(base_duty: float) -> None:
    print(
        "\nCommands:\n"
        "  <left> <right>       Set signed duty cycles directly, e.g. 45 55 or -30 30\n"
        f"  diff <value>         Test around base {base_duty:g}%: left=base+value, right=base-value\n"
        "  base <value>         Change the base used by diff commands\n"
        "  half                 Set both motors forward to 50%\n"
        "  stop                 Stop both motors\n"
        "  help                 Show this help\n"
        "  quit                 Stop, clean up GPIO, and exit\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Interactive PWM/differential motor tester for Raspberry Pi GPIO."
    )
    parser.add_argument(
        "--frequency",
        type=int,
        default=DEFAULT_PWM_HZ,
        help=f"PWM frequency in Hz. Default: {DEFAULT_PWM_HZ}",
    )
    args = parser.parse_args()

    base_duty = DEFAULT_BASE_DUTY

    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)

    pins = (
        LEFT_PWM_PIN,
        LEFT_FORWARD_PIN,
        LEFT_BACKWARD_PIN,
        RIGHT_PWM_PIN,
        RIGHT_FORWARD_PIN,
        RIGHT_BACKWARD_PIN,
    )
    for pin in pins:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

    left_pwm = GPIO.PWM(LEFT_PWM_PIN, args.frequency)
    right_pwm = GPIO.PWM(RIGHT_PWM_PIN, args.frequency)

    left_pwm.start(0)
    right_pwm.start(0)

    try:
        print("Motor PWM differential tester")
        print(f"GPIO mode: BOARD, PWM frequency: {args.frequency} Hz")
        print(f"Left PWM pin: {LEFT_PWM_PIN}, right PWM pin: {RIGHT_PWM_PIN}")
        apply_speeds(left_pwm, right_pwm, base_duty, base_duty)
        print_help(base_duty)

        while True:
            raw = input("motor-diff> ").strip()
            if not raw:
                continue

            parts = raw.split()
            command = parts[0].lower()

            try:
                if command in {"q", "quit", "exit"}:
                    break
                if command in {"h", "help", "?"}:
                    print_help(base_duty)
                    continue
                if command == "stop":
                    apply_speeds(left_pwm, right_pwm, 0, 0)
                    continue
                if command == "half":
                    base_duty = DEFAULT_BASE_DUTY
                    apply_speeds(left_pwm, right_pwm, base_duty, base_duty)
                    continue
                if command == "base":
                    if len(parts) != 2:
                        raise ValueError("usage: base <value>")
                    base_duty = abs(clamp_duty(parse_float(parts[1], "base")))
                    print(f"Base duty set to {base_duty:.1f}%")
                    continue
                if command == "diff":
                    if len(parts) != 2:
                        raise ValueError("usage: diff <value>")
                    diff = parse_float(parts[1], "diff")
                    apply_speeds(left_pwm, right_pwm, base_duty + diff, base_duty - diff)
                    continue
                if len(parts) == 2:
                    left = parse_float(parts[0], "left")
                    right = parse_float(parts[1], "right")
                    apply_speeds(left_pwm, right_pwm, left, right)
                    continue

                raise ValueError("unknown command; type help for examples")
            except ValueError as exc:
                print(f"Error: {exc}")

    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        apply_speeds(left_pwm, right_pwm, 0, 0)
        left_pwm.stop()
        right_pwm.stop()
        GPIO.cleanup()
        print("GPIO cleaned up.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
