# USB-231 DAQ Card - Voltage Measurement Application

Example applications for using the Measurement Computing USB-231 Data Acquisition device for voltage measurements.

## Prerequisites

### 1. Install DAQ Hardware Drivers
Download and install from Measurement Computing:
- **InstaCal** - Configuration and test utility
- **Universal Library for Python** (mcculw)

### 2. Install Python Dependencies

```bash
pip install mcculw pandas matplotlib
```

## Hardware Setup

### USB-231 Specifications
- **Analog Inputs**: 8 single-ended or 4 differential
- **Resolution**: 16-bit
- **Sample Rate**: Up to 100 kS/s
- **Input Ranges**: ±10V, ±5V, ±2V, ±1V

### Wiring
Connect your voltage source to the USB-231:
- **CH0+** (Pin 1) - Positive input for Channel 0
- **CH0-** (Pin 2) - Negative input for Channel 0 (or ground for single-ended)
- **AGND** (Pin 9) - Analog ground

## Files

### 1. `USB231_voltage_measurement.py`
**Full-featured application** with:
- Device discovery and connection
- Single and continuous voltage readings
- Data logging to CSV
- Statistical analysis
- Plotting capabilities
- Error handling

**Usage:**
```bash
python USB231_voltage_measurement.py
```

**Configuration (edit in file):**
```python
BOARD_NUM = 0              # Board number
CHANNEL = 0                # Channel 0-7
AI_RANGE = ULRange.BIP10VOLTS  # Voltage range
SAMPLE_RATE = 1.0          # Samples per second
NUM_SAMPLES = 100          # Total samples
```

### 2. `USB231_simple_example.py`
**Quick start example** - minimal code for basic voltage reading.

**Usage:**
```bash
python USB231_simple_example.py
```

## Voltage Ranges

| Range | Enum Value | Description |
|-------|-----------|-------------|
| ±10V | `ULRange.BIP10VOLTS` | Default, highest range |
| ±5V | `ULRange.BIP5VOLTS` | Medium range |
| ±2V | `ULRange.BIP2VOLTS` | Low range |
| ±1V | `ULRange.BIP1VOLTS` | Lowest range, best resolution |

Choose the smallest range that accommodates your signal for best resolution.

## Common Issues

### "No devices found"
- Check USB connection
- Verify drivers are installed (InstaCal)
- Run InstaCal to detect device
- Check device manager for USB-231

### "Board number is invalid"
- Default board number is 0
- Check board configuration in InstaCal

### Permission errors (Linux)
Add udev rules for USB device access:
```bash
sudo usermod -a -G dialout $USER
```

## Code Examples

### Read Single Voltage
```python
from mcculw import ul
from mcculw.enums import ULRange

# Read raw value
value = ul.a_in(0, 0, ULRange.BIP10VOLTS)

# Convert to voltage
voltage = ul.to_eng_units(0, ULRange.BIP10VOLTS, value)
print(f"Voltage: {voltage:.4f} V")
```

### Continuous Reading with Data Storage
```python
import pandas as pd
from datetime import datetime

data = []
for i in range(100):
    voltage = ul.to_eng_units(0, ULRange.BIP10VOLTS, 
                               ul.a_in(0, 0, ULRange.BIP10VOLTS))
    data.append({
        'timestamp': datetime.now(),
        'voltage': voltage
    })
    time.sleep(0.1)

df = pd.DataFrame(data)
df.to_csv('voltage_data.csv', index=False)
```

### Read Multiple Channels
```python
channels = [0, 1, 2, 3]  # Read channels 0-3

for channel in channels:
    value = ul.a_in(0, channel, ULRange.BIP10VOLTS)
    voltage = ul.to_eng_units(0, ULRange.BIP10VOLTS, value)
    print(f"Channel {channel}: {voltage:.4f} V")
```

## Output

The application will generate:
- **Console output**: Real-time voltage readings and statistics
- **CSV file**: `voltage_data_YYYYMMDD_HHMMSS.csv` with all measurements
- **Plot**: Voltage vs. time graph (if matplotlib installed)

## CSV Format

```csv
sample,timestamp,voltage
1,2026-01-23 10:30:45.123456,2.345678
2,2026-01-23 10:30:46.123456,2.346789
...
```

## Support

- **Measurement Computing**: https://www.mccdaq.com/
- **mcculw Documentation**: https://github.com/mccdaq/mcculw
- **USB-231 Manual**: Check Measurement Computing website

## License

This code is provided as an example for educational purposes.
