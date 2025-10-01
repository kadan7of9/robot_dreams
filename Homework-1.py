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
        "Frequency": "Frequency",
        "CurrentSet": "Set_current",
        "Current": "Real_current",
        "Voltage Drop": "RSM_voltage_drop",
        "Crack size": "Crack_size",
    },
    inplace=True,
)

print(dataset.head())

# Set variables for plotting
x_axis = "RSM_voltage_drop"
y_axis = "Crack_size"
hue = "Real_current"

plt.figure(figsize=(8, 6))
sns.scatterplot(data=dataset, x=x_axis, y=y_axis, hue=hue, palette="Spectral")
plt.title("PTS Crack Meter Data (Seaborn)")
plt.show()