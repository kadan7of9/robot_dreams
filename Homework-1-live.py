import dash
from dash import dcc, html
from dash.dependencies import Output, Input
import plotly.graph_objects as go
import random
from collections import deque
import pandas as pd

# Initialize Dash app
app = dash.Dash(__name__)

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


#define the path to the dataset
PATH = "datasets/crack_meter/CalibData-30kHz-0-12--.csv"

# Load the Concrete dataset
dataset = pd.read_csv(PATH, delimiter=';') # ; is used as column delimiter
# Apply Scale_current function to current columns
dataset["CurrentSet"] = dataset["CurrentSet"].apply(Scale_current)
dataset["Current"] = dataset["Current"].apply(Scale_current)
dataset["Voltage Drop"] = dataset["Voltage Drop"].apply(Scale_voltage)
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

# Set variables for plotting
x_axis = "RSM voltage drop [mV]"
y_axis = "Crack size [mm]"
z_axis = "Real current [mA]"


# Use deque for efficient data updates (fixed-length queue)
max_length = 200
x_data = deque(maxlen=max_length)
y_data = deque(maxlen=max_length)

# Initialize empty figure with one scatter trace
fig = go.Figure()
fig.add_scatter(
    x=list(x_data), y=list(y_data), mode="markers", name="Crackmeter Data"
)

# App layout: title, graph, and interval component for updates
app.layout = html.Div(
    [
        html.H1("Crack Meter Live Data Visualization"),
        dcc.Graph(id="live-graph", figure=fig),
        dcc.Interval(
            id="interval-component", interval=200, n_intervals=0  # 200ms = 0.2 second
        ),
    ]
)

# Callback to update graph every interval
@app.callback(
    Output("live-graph", "figure"), Input("interval-component", "n_intervals")
)
def update_graph(n):
    # Add 20 new data points at once from dataset
    start_index = (n * 20) % len(dataset)
    
    # Clear existing data and add 20 new points
    x_data.clear()
    y_data.clear()
    
    for i in range(20):
        data_index = (start_index + i) % len(dataset)
        x_data.append(dataset.iloc[data_index][x_axis])
        y_data.append(dataset.iloc[data_index][y_axis])
    
    # Create new figure with updated data
    fig = go.Figure()
    fig.add_scatter(
        x=list(x_data), y=list(y_data), mode="markers", name="Crackmeter Data"
    )
    fig.update_layout(xaxis_title="Voltage Drop [mV]", yaxis_title="Crack Size [mm]")
    return fig


# Run the app
if __name__ == "__main__":
    app.run(debug=True)