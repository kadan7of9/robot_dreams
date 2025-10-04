# Import necessary libraries
import pandas as pd
import seaborn as sns
import plotly.express as px
import matplotlib.pyplot as plt

PATH = "datasets/crack_meter/CalibData-30kHz-0-12--.csv"

def Scale_current(current) -> float:
    """Scale current to mA using linear polynomial approximation"""
    if current is None:
        return None
    elif current < 150:
        return 0
    elif current > 2000:
        return (147.48 + 0.0118 * current)
    else:
        return (101.97 + 0.0283 * current) # values between 150 and 2000

def Scale_voltage(voltage) -> float:
    """Scale voltage to mV"""
    if voltage is None:
        return None
    else:
        return (((2.048/(65535/2))*1000)* voltage) # AD1114 was used with 2.048V range

# Load the Concrete dataset
dataset = pd.read_csv(PATH, delimiter=';') # ; is used as column delimiter
print(dataset.head())

# Apply Scale_current function to current columns
dataset["CurrentSet"] = dataset["CurrentSet"].apply(Scale_current)
dataset["Current"] = dataset["Current"].apply(Scale_current)
dataset["Voltage Drop"] = dataset["Voltage Drop"].apply(Scale_voltage)

print("\nDataset after applying Scale_current and Scale_voltage functions:")
print(dataset.head())

# Rename columns for easier access
dataset.rename(
    columns={
        "Frequency": "Frequency [kHz]",
        "CurrentSet": "Set current [mA]",
        "Current": "Real current [mA]",
        "Voltage Drop": "RSM voltage drop [mV]",
        "Crack size": "Crack size [mm]",
    },
    inplace=True,
)

# print several rows with renamed columns
print(dataset.head())


# Set variables for plotting
x_axis = "RSM voltage drop [mV]"
y_axis = "Crack size [mm]"
z_axis = "Real current [mA]"

# Seaborn scatter plot
plt.figure(figsize=(8, 6))
sns.scatterplot(data=dataset, x=x_axis, y=y_axis, hue=z_axis, palette="Spectral")
plt.title("PTS Crack Meter Calibration Data (Seaborn)")
plt.show()

# Plotly scatter plot
fig = px.scatter(dataset, x=x_axis, y=y_axis, color=z_axis, 
                title="PTS Crack Meter Calibration Data (Plotly)")
fig.show()