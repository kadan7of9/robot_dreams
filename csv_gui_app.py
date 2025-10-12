import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np


def Scale_current(current) -> float:
    """Scale current to mA using linear polynomial approximation"""
    if current is None:
        return None
    elif current < 150:
        return 0
    elif current > 2000:
        return (147.48 + 0.0118 * current)
    else:
        return (101.97 + 0.0283 * current)  # values between 150 and 2000


def Scale_voltage(voltage) -> float:
    """Scale voltage to mV"""
    if voltage is None:
        return None
    else:
        return (((2.048/(65535/2))*1000) * voltage)  # AD1114 was used with 2.048V range


class CSVVisualizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CSV Data Visualizer")
        self.root.geometry("1000x700")
        
        # Initialize variables
        self.df = None
        self.df_original = None  # Store original data
        self.current_file = None
        
        # Create the main interface
        self.create_widgets()
        
    def create_widgets(self):
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # File selection section
        file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="5")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Button(file_frame, text="Load CSV File", 
                  command=self.load_csv_file).grid(row=0, column=0, padx=(0, 5))
        
        self.file_label = ttk.Label(file_frame, text="No file selected")
        self.file_label.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Data info section
        info_frame = ttk.LabelFrame(main_frame, text="Data Information", padding="5")
        info_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        info_frame.columnconfigure(1, weight=1)
        
        self.info_text = tk.Text(info_frame, height=4, wrap=tk.WORD)
        self.info_text.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        info_scrollbar = ttk.Scrollbar(info_frame, orient="vertical", command=self.info_text.yview)
        info_scrollbar.grid(row=0, column=2, sticky=(tk.N, tk.S))
        self.info_text.configure(yscrollcommand=info_scrollbar.set)
        
        # Plotting controls
        plot_frame = ttk.LabelFrame(main_frame, text="Plot Controls", padding="5")
        plot_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        ttk.Label(plot_frame, text="X-axis:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.x_var = ttk.Combobox(plot_frame, state="readonly")
        self.x_var.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(plot_frame, text="Y-axis:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.y_var = ttk.Combobox(plot_frame, state="readonly")
        self.y_var.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(plot_frame, text="Color (Z-axis):").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.z_var = ttk.Combobox(plot_frame, state="readonly")
        self.z_var.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Add data scaling checkbox
        self.scale_data_var = tk.BooleanVar()
        self.scale_data_check = ttk.Checkbutton(plot_frame, text="Apply Crack Meter Scaling", 
                                               variable=self.scale_data_var,
                                               command=self.on_scaling_change)
        self.scale_data_check.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(5, 5))
        
        ttk.Label(plot_frame, text="Plot Type:").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        self.plot_type = ttk.Combobox(plot_frame, values=["Line", "Scatter", "Colored Scatter", "Bar", "Histogram"], 
                                     state="readonly")
        self.plot_type.set("Scatter")
        self.plot_type.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Button(plot_frame, text="Generate Plot", 
                  command=self.generate_plot).grid(row=5, column=0, columnspan=2, 
                                                  sticky=(tk.W, tk.E), pady=(10, 0))
        
        plot_frame.columnconfigure(1, weight=1)
        
        # Plot area
        self.plot_frame = ttk.Frame(main_frame)
        self.plot_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.plot_frame.columnconfigure(0, weight=1)
        self.plot_frame.rowconfigure(0, weight=1)
        
        # Initialize matplotlib figure
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, self.plot_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add toolbar for plot interaction
        toolbar_frame = ttk.Frame(self.plot_frame)
        toolbar_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()
        
    def on_scaling_change(self):
        """Handle scaling checkbox change"""
        if self.df_original is not None:
            self.apply_data_processing()
            self.update_data_info()
            self.update_column_dropdowns()
            
    def apply_data_processing(self):
        """Apply scaling and column renaming based on checkbox state"""
        if self.df_original is None:
            return
            
        # Start with original data
        self.df = self.df_original.copy()
        
        if self.scale_data_var.get():
            # Check if this looks like crack meter data
            expected_cols = ['Frequency', 'CurrentSet', 'Current', 'Voltage Drop', 'Crack size']
            if all(col in self.df.columns for col in expected_cols):
                # Apply scaling functions
                self.df["CurrentSet"] = self.df["CurrentSet"].apply(Scale_current)
                self.df["Current"] = self.df["Current"].apply(Scale_current)
                self.df["Voltage Drop"] = self.df["Voltage Drop"].apply(Scale_voltage)
                
                # Rename columns for easier access
                self.df.rename(
                    columns={
                        "Frequency": "Frequency [kHz]",
                        "CurrentSet": "Set current [mA]",
                        "Current": "Real current [mA]",
                        "Voltage Drop": "RSM voltage drop [mV]",
                        "Crack size": "Crack size [mm]",
                    },
                    inplace=True,
                )
        
    def load_csv_file(self):
        """Open file dialog and load CSV file"""
        file_path = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                # Load CSV file - try different separators
                try:
                    self.df_original = pd.read_csv(file_path, sep=';')
                except:
                    # Try with comma separator
                    self.df_original = pd.read_csv(file_path)
                    
                self.current_file = file_path
                
                # Check if this looks like crack meter data and enable scaling by default
                expected_cols = ['Frequency', 'CurrentSet', 'Current', 'Voltage Drop', 'Crack size']
                if all(col in self.df_original.columns for col in expected_cols):
                    self.scale_data_var.set(True)
                
                # Apply data processing based on checkbox state
                self.apply_data_processing()
                
                # Update file label
                filename = file_path.split('/')[-1]
                self.file_label.config(text=f"Loaded: {filename}")
                
                # Update data information
                self.update_data_info()
                
                # Update column dropdowns
                self.update_column_dropdowns()
                
                messagebox.showinfo("Success", f"Successfully loaded {len(self.df)} rows of data!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load CSV file:\n{str(e)}")
                
    def update_data_info(self):
        """Update the data information text widget"""
        if self.df is not None:
            info = []
            info.append(f"Rows: {len(self.df)}")
            info.append(f"Columns: {len(self.df.columns)}")
            info.append(f"Column names: {', '.join(self.df.columns.tolist())}")
            info.append(f"Data types:\n{self.df.dtypes.to_string()}")
            
            # Add basic statistics for numeric columns
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                info.append(f"\nNumeric columns statistics:")
                info.append(self.df[numeric_cols].describe().to_string())
                
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(1.0, "\n".join(info))
            
    def update_column_dropdowns(self):
        """Update the column selection dropdowns"""
        if self.df is not None:
            columns = self.df.columns.tolist()
            
            # Update x, y, and z axis dropdowns
            self.x_var['values'] = columns
            self.y_var['values'] = columns
            self.z_var['values'] = ['None'] + columns  # Add 'None' option for z-axis
            
            # Set default selections
            # Check if this is processed crack meter data and set appropriate defaults
            if 'RSM voltage drop [mV]' in columns and 'Crack size [mm]' in columns and 'Real current [mA]' in columns:
                self.x_var.set('RSM voltage drop [mV]')
                self.y_var.set('Crack size [mm]')
                self.z_var.set('Real current [mA]')
            else:
                # Default selections for other data
                if len(columns) > 0:
                    self.x_var.set(columns[0])
                if len(columns) > 1:
                    self.y_var.set(columns[1])
                if len(columns) > 2:
                    self.z_var.set(columns[2])
                else:
                    self.z_var.set('None')
                
    def generate_plot(self):
        """Generate plot based on selected options"""
        if self.df is None:
            messagebox.showwarning("Warning", "Please load a CSV file first!")
            return
            
        x_col = self.x_var.get()
        y_col = self.y_var.get()
        z_col = self.z_var.get()
        plot_type = self.plot_type.get()
        
        if not x_col or not y_col:
            messagebox.showwarning("Warning", "Please select both X and Y columns!")
            return
            
        try:
            # Clear previous plot
            self.ax.clear()
            
            # Generate plot based on type
            if plot_type == "Line":
                self.ax.plot(self.df[x_col], self.df[y_col], marker='o', linewidth=1, markersize=3)
            elif plot_type == "Scatter":
                self.ax.scatter(self.df[x_col], self.df[y_col], alpha=0.7)
            elif plot_type == "Colored Scatter":
                if z_col and z_col != 'None':
                    # Create colored scatter plot
                    scatter = self.ax.scatter(self.df[x_col], self.df[y_col], 
                                            c=self.df[z_col], cmap='Spectral', 
                                            alpha=0.7, s=20)
                    # Add colorbar
                    cbar = plt.colorbar(scatter, ax=self.ax)
                    cbar.set_label(z_col)
                else:
                    # Fallback to regular scatter if no z-column selected
                    self.ax.scatter(self.df[x_col], self.df[y_col], alpha=0.7)
                    messagebox.showinfo("Info", "No color column selected. Showing regular scatter plot.")
            elif plot_type == "Bar":
                # For bar plots, we'll aggregate data if there are too many unique values
                if self.df[x_col].nunique() > 50:
                    messagebox.showwarning("Warning", 
                                         "Too many unique X values for bar plot. Consider using scatter or line plot.")
                    return
                self.ax.bar(self.df[x_col], self.df[y_col])
            elif plot_type == "Histogram":
                # For histogram, we'll plot the distribution of the selected column
                self.ax.hist(self.df[y_col], bins=30, alpha=0.7, edgecolor='black')
                self.ax.set_xlabel(y_col)
                self.ax.set_ylabel('Frequency')
                self.ax.set_title(f'Histogram of {y_col}')
                self.canvas.draw()
                return
                
            # Set labels and title
            self.ax.set_xlabel(x_col)
            self.ax.set_ylabel(y_col)
            
            # Create appropriate title
            if plot_type == "Colored Scatter" and z_col and z_col != 'None':
                title = f'{plot_type}: {y_col} vs {x_col} (colored by {z_col})'
            else:
                title = f'{plot_type}: {y_col} vs {x_col}'
            
            self.ax.set_title(title)
            self.ax.grid(True, alpha=0.3)
            
            # Update canvas
            self.canvas.draw()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate plot:\n{str(e)}")


def main():
    root = tk.Tk()
    app = CSVVisualizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()