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

# Nahrati environment promenych z .env souboru
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed. Using system environment variables only.")

# Ziskani API klice z environment promenych
API_KEY = getenv("API_KEY")

def get_ip():
    """Get public IP address using ipify.org API."""
    url = "https://api.ipify.org/"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Error: HTTP {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
    
def get_location(ip: str, format: str):
    """Get location information for an IP address in specified format."""
    try:
        response = requests.get(f"http://ip-api.com/{format}/{ip}", timeout=5)
        if response.status_code == 200:
            data = response.text
            return data
        else:
            print(f"Error: HTTP {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {e}")
        return None

def get_real_time_weather(lat: float, lon: float):
    """Get real-time weather data for given latitude and longitude."""
    # Priprava URL pro API volani
    url = (
        f"https://api.tomorrow.io/v4/weather/realtime?"
        f"location={lat},{lon}"
        f"&apikey={API_KEY}"
        "&units=metric"  # Chceme zivot v metrickych jednotkach
    )

    # Nastaveni hlavicek pro dodatenou kompresi
    headers = {"accept": "application/json", "accept-encoding": "deflate, gzip, br"}
    try:
        # Zavolani prikazu GET na weather API
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Error: HTTP {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {e}")
        return None

class WeatherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Weather Application with World Map")
        self.root.geometry("1200x700")
        self.root.configure(bg='#f0f0f0')
        
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Initialize location variables
        self.current_lat = None
        self.current_lon = None
        
        # Create the GUI elements
        self.create_widgets()
        
        # Create initial world map
        self.create_simple_world_map()
        
    def create_widgets(self):
        """Create and layout the GUI widgets"""
        
        # Main horizontal paned window
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left frame for weather info
        left_frame = ttk.Frame(main_paned, padding="15")
        main_paned.add(left_frame, weight=1)
        
        # Right frame for map
        right_frame = ttk.Frame(main_paned, padding="15")
        main_paned.add(right_frame, weight=2)
        
        # === LEFT SIDE - Weather Information ===
        
        # Title
        title_label = tk.Label(
            left_frame, 
            text="Weather Information", 
            font=('Arial', 16, 'bold'),
            bg='#f0f0f0',
            fg='#2c3e50'
        )
        title_label.pack(pady=(0, 20))
        
        # Tlacitko pro ziskani pozice pocitace (ziska se verejna IP adresa)
        self.get_position_btn = tk.Button(
            left_frame,
            text="Get Position",
            font=('Arial', 12, 'bold'),
            bg='#3498db',
            fg='white',
            relief=tk.RAISED,
            bd=2,
            width=15,
            height=2,
            cursor='hand2',
            command=self.get_position_and_weather
        )
        self.get_position_btn.pack(pady=10)
        
        # Weather Data Label (with frame for better styling)
        data_frame = ttk.LabelFrame(left_frame, text="Weather Data", padding="10")
        data_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        # Weather information label
        self.weather_label = tk.Label(
            data_frame,
            text="Click 'Get Position' to fetch weather data and see your location on the world map",
            font=('Arial', 10),
            bg='white',
            fg='#34495e',
            justify=tk.LEFT,
            anchor='nw',
            wraplength=350,
            relief=tk.SUNKEN,
            bd=1
        )
        self.weather_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Status label
        self.status_label = tk.Label(
            left_frame,
            text="Ready - World map loaded",
            font=('Arial', 9),
            bg='#f0f0f0',
            fg='#7f8c8d'
        )
        self.status_label.pack(pady=(10, 0))
        
        # === RIGHT SIDE - World Map ===
        
        # Map title
        self.map_title_label = tk.Label(
            right_frame, 
            text="World Map - Location Viewer", 
            font=('Arial', 14, 'bold'),
            bg='#f0f0f0',
            fg='#2c3e50'
        )
        self.map_title_label.pack(pady=(0, 10))
        
        # Map frame for matplotlib canvas
        self.map_frame = ttk.LabelFrame(right_frame, text="Interactive World Map", padding="5")
        self.map_frame.pack(fill=tk.BOTH, expand=True)
        
    def create_simple_world_map(self):
        """Create a simple but effective world map using matplotlib"""
        # Clear any existing canvas
        for widget in self.map_frame.winfo_children():
            widget.destroy()
            
        # Create figure and axis
        self.fig, self.ax = plt.subplots(figsize=(8, 5))
        self.fig.patch.set_facecolor('#f0f0f0')
        
        # Set limits
        self.ax.set_xlim(-180, 180)
        self.ax.set_ylim(-90, 90)
        
        # Create simple world outline (ocean background)
        world_x = [-180, 180, 180, -180, -180]
        world_y = [-90, -90, 90, 90, -90]
        self.ax.fill(world_x, world_y, color='lightblue', alpha=0.3, label='Ocean')
        
        # Add major landmasses (simplified)
        continents = {
            'North America': ([-170, -50, -50, -170, -170], [20, 20, 80, 80, 20]),
            'South America': ([-90, -30, -30, -90, -90], [-60, -60, 15, 15, -60]),
            'Europe': ([-10, 70, 70, -10, -10], [35, 35, 75, 75, 35]),
            'Africa': ([-20, 55, 55, -20, -20], [-35, -35, 40, 40, -35]),
            'Asia': ([25, 180, 180, 25, 25], [5, 5, 80, 80, 5]),
            'Australia': ([110, 180, 180, 110, 110], [-45, -45, -10, -10, -45])
        }
        
        # Draw continents
        for continent, (x_coords, y_coords) in continents.items():
            self.ax.fill(x_coords, y_coords, color='lightgreen', alpha=0.6, 
                        edgecolor='darkgreen', linewidth=1)
            
            # Add continent labels
            center_x = sum(x_coords[:-1]) / (len(x_coords) - 1)
            center_y = sum(y_coords[:-1]) / (len(y_coords) - 1)
            self.ax.text(center_x, center_y, continent, ha='center', va='center', 
                        fontsize=8, fontweight='bold', alpha=0.7)
        
        # Add grid
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlabel('Longitude °', fontsize=10)
        self.ax.set_ylabel('Latitude °', fontsize=10)
        self.ax.set_title('World Map - Your Location', fontsize=12, fontweight='bold')
        
        # Add equator and prime meridian
        self.ax.axhline(y=0, color='blue', linestyle='--', alpha=0.5, linewidth=1, label='Equator')
        self.ax.axvline(x=0, color='blue', linestyle='--', alpha=0.5, linewidth=1, label='Prime Meridian')
        
        # Add location marker if available
        if self.current_lat is not None and self.current_lon is not None:
            self.ax.plot(self.current_lon, self.current_lat, 'ro', markersize=12, 
                        markerfacecolor='red', markeredgecolor='darkred', markeredgewidth=2,
                        label='Your Location')
            self.ax.text(self.current_lon, self.current_lat + 8, 'Your Location', 
                        ha='center', va='bottom', fontweight='bold', fontsize=10,
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.8))
        
        # Adjust layout
        plt.tight_layout()
        
        # Embed in tkinter using FigureCanvasTkAgg
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.map_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def update_map_with_location(self, lat, lon, city, country):
        """Update the map to show the current location"""
        # Store location
        self.current_lat = lat
        self.current_lon = lon
        
        # Update map title
        self.map_title_label.config(text=f"World Map - {city}, {country}")
        
        # Recreate the map with the new location
        self.create_simple_world_map()
        
        # Update status
        self.status_label.config(text=f"Location marked: {city}, {country}")
        
    def get_position_and_weather(self):
        """Get user position and fetch weather data"""
        try:
            # Update status
            self.status_label.config(text="Getting position...")
            self.root.update()
            
            # Get position using IP geolocation
            ip = get_ip()
            print(f"DEBUG - Got IP: {ip}")
            if not ip:
                raise Exception("Failed to get IP address")
            
            # Get location data as JSON string
            location_json = get_location(ip, "json")
            if not location_json:
                raise Exception("Failed to get location data")
            
            # Parse the JSON string to extract lat and lon
            location_data = json.loads(location_json)
            
            # Check if the request was successful
            if location_data.get("status") != "success":
                raise Exception("Location API request failed")
            
            # Extract latitude and longitude
            lat = location_data.get("lat")
            lon = location_data.get("lon")
            city = location_data.get("city")
            country = location_data.get("country")
            
            if lat is None or lon is None:
                raise Exception("Could not extract coordinates from location data")
            
            # Update the map with the new location
            self.update_map_with_location(lat, lon, city, country)
            
            # Update status
            self.status_label.config(text=f"Getting weather for {city}, {country}...")
            self.root.update()
            
            # Get weather data using extracted coordinates
            weather_data = get_real_time_weather(lat, lon)
            
            if not weather_data:
                raise Exception("Failed to get weather data - API returned no data")
            
            # Format and display the weather information
            self.display_weather_data(weather_data, location_data)
            self.status_label.config(text="Weather data updated successfully")
            
        except json.JSONDecodeError as e:
            error_message = f"JSON parsing error: {str(e)}"
            self.weather_label.config(text=error_message)
            self.status_label.config(text="JSON parsing failed")
            messagebox.showerror("JSON Error", error_message)
        except Exception as e:
            error_message = f"Error: {str(e)}"
            self.weather_label.config(text=error_message)
            self.status_label.config(text="Error occurred")
            messagebox.showerror("Error", error_message)

    def display_weather_data(self, weather_data, location_data):
        """Format and display weather data in the label"""
        try:
            # Extract location information
            city = location_data.get("city", "Unknown")
            country = location_data.get("country", "Unknown")
            lat = location_data.get("lat", 0)
            lon = location_data.get("lon", 0)
            
            # Extract weather information from Tomorrow.io API response
            if "data" in weather_data:
                values = weather_data["data"]["values"]
                
                temperature = values.get("temperature", "N/A")
                humidity = values.get("humidity", "N/A")
                wind_speed = values.get("windSpeed", "N/A")
                visibility = values.get("visibility", "N/A")
                
                # Get timestamp from the API response
                time_info = weather_data.get("data", {}).get("time", "Unknown time")
                
                # Format the weather information
                weather_info = f"""📍 Location: {city}, {country}
🌐 Coordinates: {lat:.4f}, {lon:.4f}

🌡️ Temperature: {temperature}°C
💧 Humidity: {humidity}%
💨 Wind Speed: {wind_speed} km/h
👁️ Visibility: {visibility} km

📡 Data from Tomorrow.io API
🕐 Last updated: {time_info}

🗺️ Your location is marked on the map with a red dot!"""
                
            else:
                weather_info = f"""📍 Location: {city}, {country}
🌐 Coordinates: {lat:.4f}, {lon:.4f}

❌ Weather data format not recognized
Raw data: {str(weather_data)[:200]}...

🗺️ Location marked on world map."""
            
            self.weather_label.config(text=weather_info)
            
        except Exception as e:
            error_info = f"Error formatting weather data: {str(e)}\n\nRaw weather data:\n{str(weather_data)[:300]}..."
            self.weather_label.config(text=error_info)
            print(f"Debug - Full weather data: {weather_data}")
    
    def on_closing(self):
        """Handle the window close event"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.root.quit()
            self.root.destroy()


def main():
    """Main function to run the application"""
    root = tk.Tk()
    app = WeatherApp(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Application closed by user")


if __name__ == "__main__":
    main()