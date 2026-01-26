"""
Simple USB-231 DAQ Card Example
Quick start for voltage measurement
"""

from mcculw import ul
from mcculw.enums import ULRange
from mcculw.ul import ULError
import time

# Configuration
BOARD_NUM = 0
CHANNEL = 0
VOLTAGE_RANGE = ULRange.BIP10VOLTS  # ±10V


def simple_voltage_read():
    """Simple example to read voltage from USB-231."""
    try:
        # Read voltage value
        value = ul.a_in(BOARD_NUM, CHANNEL, VOLTAGE_RANGE)

        # Convert to engineering units (volts)
        voltage = ul.to_eng_units(BOARD_NUM, VOLTAGE_RANGE, value)

        print(f"Channel {CHANNEL}: {voltage:.4f} V")
        return voltage

    except ULError as e:
        print(f"Error: {e}")
        return None


def continuous_read(duration_seconds=10):
    """Read voltage continuously for specified duration."""
    print(f"Reading voltage for {duration_seconds} seconds...")
    print("Press Ctrl+C to stop\n")

    start_time = time.time()
    sample_count = 0

    try:
        while (time.time() - start_time) < duration_seconds:
            voltage = simple_voltage_read()
            sample_count += 1
            time.sleep(0.5)  # Read every 0.5 seconds

    except KeyboardInterrupt:
        print("\nStopped by user")

    print(f"\nTotal samples: {sample_count}")


if __name__ == "__main__":
    print("USB-231 Simple Voltage Reader")
    print("-" * 40)
    continuous_read(duration_seconds=10)
