import pandas as pd
import seaborn as sns
import plotly.express as px
import matplotlib.pyplot as plt

PATH = "datasets/crack_meter/CalibData-30kHz-0-12--.csv"

# Load the Concrete dataset
dataset = pd.read_csv(PATH, delimiter=';')
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

print(dataset.head())

# Set variables for plotting
x_axis = "RSM voltage drop [mV]"
y_axis = "Crack size [mm]"
hue = "Real current [mA]"

plt.figure(figsize=(8, 6))
sns.scatterplot(data=dataset, x=x_axis, y=y_axis, hue=hue, palette="Spectral")
plt.title("PTS Crack Meter Calibration Data (Seaborn)")
plt.show()