"""
USB-231 Simple Voltage Measurement with Graph
Measures 1000 points and displays them in a graph
Based on USB231_voltage_measurement.py
"""

import time
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from ctypes import cast, POINTER, c_double
from mcculw import ul
from mcculw.enums import ULRange, InterfaceType, ScanOptions, FunctionType, Status
from mcculw.ul import ULError
from mcculw.device_info import DaqDeviceInfo

# Configuration
BOARD_NUM = 0  # Board number (default is 0)
CHANNEL = 0  # Analog input channel (0-7 for USB-231)
AI_RANGE = ULRange.BIP10VOLTS  # ±10V range
NUM_SAMPLES = 1000  # Number of samples to collect
SAMPLE_RATE = 10000.0  # Sampling rate in Hz


def discover_and_connect():
    """Discover and connect to USB-231 device."""
    print("Scanning for DAQ devices...")

    try:
        # Try to release the board first in case it's already in use
        try:
            ul.release_daq_device(BOARD_NUM)
            time.sleep(0.5)
        except:
            pass

        # Discover devices
        devices = ul.get_daq_device_inventory(InterfaceType.USB)

        if not devices:
            print("No DAQ devices found!")
            return False

        print(f"Found {len(devices)} device(s):")
        for i, device in enumerate(devices):
            print(f"  [{i}] {device.product_name} - {device.unique_id}")

        # Create the DAQ device
        try:
            ul.create_daq_device(BOARD_NUM, devices[0])
            print(f"Connected to {devices[0].product_name}")
            return True
        except ULError as e:
            if "already in use" in str(e).lower():
                print("Device already in use - attempting to use existing connection")
                return True
            raise

    except ULError as e:
        print(f"Error connecting to device: {e}")
        return False


def measure_and_plot():
    """Measure 1000 voltage samples in one shot and plot them."""
    print(f"\nMeasuring {NUM_SAMPLES} samples at {SAMPLE_RATE} Hz...")
    print(f"Channel: {CHANNEL}")
    print(f"Range: ±10V")
    print(f"Acquisition mode: Hardware-timed (one shot)")
    print("-" * 50)

    try:
        # Allocate memory buffer for scaled data (float64)
        memhandle = ul.scaled_win_buf_alloc(NUM_SAMPLES)

        # Get pointer to the buffer
        ctypes_array = cast(memhandle, POINTER(c_double))

        # Configure scan options (SCALEDATA for direct voltage values)
        scan_options = ScanOptions.SCALEDATA

        print("Starting data acquisition...")
        start_time = time.time()

        # Perform the scan (one shot, NUM_SAMPLES total)
        actual_rate = ul.a_in_scan(
            BOARD_NUM,
            CHANNEL,
            CHANNEL,  # low_chan = high_chan for single channel
            NUM_SAMPLES,
            int(SAMPLE_RATE),
            AI_RANGE,
            memhandle,
            scan_options,
        )

        # Wait for scan to complete
        while True:
            status, cur_count, cur_index = ul.get_status(
                BOARD_NUM, FunctionType.AIFUNCTION
            )
            if status == Status.IDLE:
                break
            time.sleep(0.01)

        elapsed_time = time.time() - start_time

        # Convert buffer to numpy array
        voltages = np.ctypeslib.as_array(ctypes_array, shape=(NUM_SAMPLES,))
        voltages = voltages.copy()  # Make a copy before freeing buffer

        # Free the buffer
        ul.win_buf_free(memhandle)

        print("-" * 50)
        print(f"Measurement complete in {elapsed_time:.3f} seconds!")
        print(f"Actual sample rate: {actual_rate:.1f} Hz")

        # Calculate statistics
        mean_v = np.mean(voltages)
        min_v = np.min(voltages)
        max_v = np.max(voltages)
        std_v = np.std(voltages)

        print(f"\nStatistics:")
        print(f"  Mean: {mean_v:.6f} V")
        print(f"  Min:  {min_v:.6f} V")
        print(f"  Max:  {max_v:.6f} V")
        print(f"  Std:  {std_v:.6f} V")

        # Plot the data
        print("\nGenerating plots...")
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

        # Time domain plot
        ax1.plot(range(len(voltages)), voltages, linewidth=1, color="blue")
        ax1.set_title(
            f"USB-231 Voltage Measurement - {NUM_SAMPLES} Samples",
            fontsize=14,
            fontweight="bold",
        )
        ax1.set_xlabel("Sample Number")
        ax1.set_ylabel("Voltage (V)")
        ax1.grid(True, alpha=0.3)

        # Calculate FFT
        voltages_array = np.array(voltages)
        # Remove DC component for better FFT visualization
        voltages_ac = voltages_array - mean_v

        # Compute FFT
        fft_result = np.fft.rfft(voltages_ac)
        fft_magnitude = np.abs(fft_result) * 2.0 / len(voltages)  # Scale properly
        fft_freq = np.fft.rfftfreq(len(voltages), 1.0 / SAMPLE_RATE)

        # FFT plot
        ax2.plot(fft_freq, fft_magnitude, linewidth=1, color="red")
        ax2.set_title("Frequency Spectrum (FFT)", fontsize=14, fontweight="bold")
        ax2.set_xlabel("Frequency (Hz)")
        ax2.set_ylabel("Magnitude (V)")
        ax2.set_xlim(0, SAMPLE_RATE / 2)  # Show up to Nyquist frequency
        ax2.grid(True, alpha=0.3)

        # Find and display dominant frequency
        if len(fft_freq) > 1:
            # Ignore DC component (index 0)
            dominant_idx = np.argmax(fft_magnitude[1:]) + 1
            dominant_freq = fft_freq[dominant_idx]
            dominant_mag = fft_magnitude[dominant_idx]
            print(
                f"\nDominant frequency: {dominant_freq:.2f} Hz (Magnitude: {dominant_mag:.6f} V)"
            )

        plt.tight_layout()

        # Save the plot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"voltage_plot_{timestamp}.png"
        plt.savefig(filename)
        print(f"Plot saved as: {filename}")

        # Display the plot
        plt.show()

        return voltages

    except ULError as e:
        print(f"UL Error during measurement: {e}")
        return None

    except KeyboardInterrupt:
        print("\nMeasurement interrupted by user.")
        return None

    except Exception as e:
        print(f"Error during measurement: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """Main application function."""
    print("=" * 60)
    print("USB-231 Simple Voltage Measurement with Graph")
    print("=" * 60)

    # Connect to device
    if not discover_and_connect():
        print("\nFailed to connect to DAQ device.")
        print("Please ensure:")
        print("  1. USB-231 is connected")
        print("  2. Drivers are installed")
        return

    try:
        # Measure and plot
        voltages = measure_and_plot()

        if voltages:
            print(f"\nSuccessfully measured {len(voltages)} samples")

    except KeyboardInterrupt:
        print("\nApplication terminated by user.")

    finally:
        # Release the DAQ device
        try:
            ul.release_daq_device(BOARD_NUM)
            print("\nDAQ device released.")
        except:
            pass

    print("Application finished.")


if __name__ == "__main__":
    main()
