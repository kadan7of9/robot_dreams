import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import requests
import json
from pprint import pprint
from os import getenv

# Get API key from environment variable for security
API_KEY = getenv("API_KEY")

def main():
    root = tk.Tk()
    root.title("Local Weather Data Visualization")
    root.geometry("800x600")




if __name__ == "__main__":
    main()
