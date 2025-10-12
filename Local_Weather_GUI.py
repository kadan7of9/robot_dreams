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

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed. Using system environment variables only.")

# Get API key from environment variable for security
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
    # Construct API URL with location and parameters
    url = (
        f"https://api.tomorrow.io/v4/weather/realtime?"
        f"location={lat},{lon}"
        f"&apikey={API_KEY}"
        "&units=metric"  # Use metric units (Celsius, km/h, etc.)
    )

    # Set request headers for optimal response
    headers = {"accept": "application/json", "accept-encoding": "deflate, gzip, br"}
    try:
        # Make GET request to the weather API
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
        self.root.title("Weather Application")
        self.root.geometry("500x400")
        self.root.configure(bg='#f0f0f0')
        
        # Create the GUI elements
        self.create_widgets()
        
    def create_widgets(self):
        """Create and layout the GUI widgets"""
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(
            main_frame, 
            text="Weather Information", 
            font=('Arial', 16, 'bold'),
            bg='#f0f0f0',
            fg='#2c3e50'
        )
        title_label.pack(pady=(0, 20))
        
        # Get Position Button
        self.get_position_btn = tk.Button(
            main_frame,
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
        data_frame = ttk.LabelFrame(main_frame, text="Weather Data", padding="10")
        data_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        # Weather information label
        self.weather_label = tk.Label(
            data_frame,
            text="Click 'Get Position' to fetch weather data",
            font=('Arial', 10),
            bg='white',
            fg='#34495e',
            justify=tk.LEFT,
            anchor='nw',
            wraplength=400,
            relief=tk.SUNKEN,
            bd=1
        )
        self.weather_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Status label
        self.status_label = tk.Label(
            main_frame,
            text="Ready",
            font=('Arial', 9),
            bg='#f0f0f0',
            fg='#7f8c8d'
        )
        self.status_label.pack(pady=(10, 0))
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
            
            # Update status
            self.status_label.config(text=f"Getting weather for {city}, {country}...")
            self.root.update()
            
            # Get weather data using extracted coordinates
            weather_data = get_real_time_weather(lat, lon)
            
            # This is line 184 where it crashes
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
🕐 Last updated: {time_info}"""
                
            else:
                weather_info = f"""📍 Location: {city}, {country}
🌐 Coordinates: {lat:.4f}, {lon:.4f}

❌ Weather data format not recognized
Raw data: {str(weather_data)[:200]}..."""
            
            self.weather_label.config(text=weather_info)
            
        except Exception as e:
            error_info = f"Error formatting weather data: {str(e)}\n\nRaw weather data:\n{str(weather_data)[:300]}..."
            self.weather_label.config(text=error_info)
            print(f"Debug - Full weather data: {weather_data}")  # Add this for debugging


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