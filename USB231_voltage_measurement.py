"""
USB-231 DAQ Card - Voltage Measurement Application
Measurement Computing USB-231 Data Acquisition Device

Specifications:
- Maximum Sample Rate: 50 kS/s (50,000 samples per second)
- Input Voltage Range: ±10 V (fixed, not configurable)
- Analog Inputs: 8 single-ended or 4 differential
- Resolution: 16-bit

Reference: https://files.digilent.com/manuals/USB-231.pdf
"""

import sys
import time
from datetime import datetime
import pandas as pd
from mcculw import ul
from mcculw.enums import ULRange, InterfaceType
from mcculw.ul import ULError
from mcculw.device_info import DaqDeviceInfo

# Configuration
BOARD_NUM = 0  # Board number (default is 0)
CHANNEL = 0  # Analog input channel (0-7 for USB-231)
AI_RANGE = ULRange.BIP10VOLTS  # ±10V range (ONLY option for USB-231)
SAMPLE_RATE = 100.0  # Sampling rate in Hz (max: 50,000 Hz for USB-231)
NUM_SAMPLES = 1000  # Number of samples to collect


def discover_daq_devices():
    """Discover and display available DAQ devices."""
    print("Scanning for DAQ devices...")

    try:
        devices = ul.get_daq_device_inventory(InterfaceType.USB)

        if not devices:
            print("No DAQ devices found!")
            return None

        print(f"\nFound {len(devices)} device(s):")
        for i, device in enumerate(devices):
            print(f"  [{i}] {device.product_name} - {device.unique_id}")

        return devices

    except ULError as e:
        print(f"Error discovering devices: {e}")
        return None


def connect_to_device(board_num=0):
    """
    Connect to the USB-231 DAQ device.

    Args:
        board_num: Board number (default 0)

    Returns:
        DaqDeviceInfo object or None if connection fails
    """
    try:
        # Try to release the board first in case it's already in use
        try:
            ul.release_daq_device(board_num)
            print("Released existing board connection.")
            time.sleep(0.5)  # Wait for release to complete
        except:
            pass  # Board wasn't in use, continue

        # Discover devices
        devices = discover_daq_devices()

        if not devices:
            print("No devices available to connect.")
            return None

        # Create the DAQ device from the first device descriptor
        try:
            ul.create_daq_device(board_num, devices[0])
        except ULError as e:
            if "already in use" in str(e).lower():
                print("\nDevice is in use by another application.")
                print(
                    "Attempting to ignore existing board and use direct connection..."
                )
                # Try to get device info without creating new device
                try:
                    daq_dev_info = DaqDeviceInfo(board_num)
                    return daq_dev_info
                except:
                    print(
                        "Unable to connect to device. Please close any other applications using the USB-231."
                    )
                    return None
            raise

    except ULError as e:
        print(f"Error connecting to device: {e}")
        return None


def read_single_voltage(board_num, channel, ai_range=ULRange.BIP10VOLTS):
    """
    Read a single voltage value from specified channel.

    Args:
        board_num: Board number
        channel: Analog input channel (0-7)
        ai_range: Voltage range (always ±10V for USB-231)

    Returns:
        Voltage value in volts (range: -10.0 to +10.0)
    """
    try:
        # Read raw value from A/D
        value = ul.a_in(board_num, channel, ai_range)

        # Convert to voltage
        eng_units_value = ul.to_eng_units(board_num, ai_range, value)

        return eng_units_value

    except ULError as e:
        print(f"Error reading voltage: {e}")
        return None


def continuous_voltage_reading(board_num, channel, ai_range, sample_rate, num_samples):
    """
    Continuously read voltage values and store in DataFrame.

    Args:
        board_num: Board number
        channel: Analog input channel (0-7)
        ai_range: Voltage range (±10V for USB-231)
        sample_rate: Sampling rate in Hz (max 50,000 Hz)
        num_samples: Total number of samples to collect

    Returns:
        pandas DataFrame with timestamp and voltage data
    """
    print(f"\nStarting continuous voltage measurement...")
    print(f"Channel: {channel}")
    print(f"Range: ±10 V (fixed for USB-231)")
    print(f"Sample Rate: {sample_rate} Hz (max: 50 kS/s)")
    print(f"Total Samples: {num_samples}")
    print("-" * 50)

    data = []
    sample_interval = 1.0 / sample_rate

    try:
        for i in range(num_samples):
            # Read voltage
            voltage = read_single_voltage(board_num, channel, ai_range)

            if voltage is not None:
                timestamp = datetime.now()
                data.append(
                    {"sample": i + 1, "timestamp": timestamp, "voltage": voltage}
                )

                # Display progress
                if (i + 1) % 10 == 0 or i == 0:
                    print(
                        f"Sample {i+1}/{num_samples}: {voltage:.6f} V at {timestamp.strftime('%H:%M:%S.%f')[:-3]}"
                    )

            # Wait for next sample
            if i < num_samples - 1:
                time.sleep(sample_interval)

        # Create DataFrame
        df = pd.DataFrame(data)

        print("-" * 50)
        print(f"Data collection complete!")
        print(f"\nStatistics:")
        print(f"  Mean Voltage: {df['voltage'].mean():.6f} V")
        print(f"  Min Voltage:  {df['voltage'].min():.6f} V")
        print(f"  Max Voltage:  {df['voltage'].max():.6f} V")
        print(f"  Std Dev:      {df['voltage'].std():.6f} V")

        return df

    except KeyboardInterrupt:
        print("\nMeasurement interrupted by user.")
        if data:
            return pd.DataFrame(data)
        return None

    except Exception as e:
        print(f"Error during measurement: {e}")
        if data:
            return pd.DataFrame(data)
        return None


def save_to_csv(df, filename=None):
    """
    Save voltage data to CSV file.

    Args:
        df: pandas DataFrame with voltage data
        filename: Output filename (optional)
    """
    if df is None or df.empty:
        print("No data to save.")
        return

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"voltage_data_{timestamp}.csv"

    try:
        df.to_csv(filename, index=False)
        print(f"\nData saved to: {filename}")
        print(f"Total records: {len(df)}")

    except Exception as e:
        print(f"Error saving data: {e}")


def plot_voltage_data(df):
    """
    Plot voltage data over time.

    Args:
        df: pandas DataFrame with voltage data
    """
    if df is None or df.empty:
        print("No data to plot.")
        return

    try:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(12, 6))
        plt.plot(df["sample"], df["voltage"], marker="o", markersize=3, linewidth=1)
        plt.title("Voltage Measurement - USB-231 DAQ", fontsize=14, fontweight="bold")
        plt.xlabel("Sample Number")
        plt.ylabel("Voltage (V)")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()

    except ImportError:
        print("matplotlib not installed. Skipping plot.")
    except Exception as e:
        print(f"Error plotting data: {e}")


def main():
    """Main application function."""
    print("=" * 60)
    print("USB-231 DAQ Card - Voltage Measurement Application")
    print("=" * 60)

    # Connect to device
    daq_info = connect_to_device(BOARD_NUM)

    if daq_info is None:
        print("\nFailed to connect to DAQ device.")
        print("Please ensure:")
        print("  1. USB-231 is connected")
        print("  2. Drivers are installed (InstaCal/Universal Library)")
        print("  3. Device is properly configured")
        return

    try:
        # Single voltage reading example
        print("\n" + "=" * 60)
        print("Single Voltage Reading Test")
        print("=" * 60)

        voltage = read_single_voltage(BOARD_NUM, CHANNEL, AI_RANGE)
        if voltage is not None:
            print(f"Channel {CHANNEL}: {voltage:.6f} V")

        # Wait a moment
        time.sleep(2)

        # Continuous voltage measurement
        print("\n" + "=" * 60)
        print("Continuous Voltage Measurement")
        print("=" * 60)

        df = continuous_voltage_reading(
            BOARD_NUM, CHANNEL, AI_RANGE, SAMPLE_RATE, NUM_SAMPLES
        )

        # Save data to CSV
        if df is not None and not df.empty:
            save_to_csv(df)

            # Plot data
            plot_voltage_data(df)

    except KeyboardInterrupt:
        print("\nApplication terminated by user.")

    finally:
        # Release the DAQ device
        try:
            ul.release_daq_device(BOARD_NUM)
            print("\nDAQ device released.")
        except:
            pass

    print("\nApplication finished.")


if __name__ == "__main__":
    main()
