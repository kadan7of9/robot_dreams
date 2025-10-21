3  # Homework-2.py
# Weather Data Retrieval Script with Open-Meteo Integration
# https://open-meteo.com/en/docs?hourly=rain&forecast_days=16

from http.client import responses
import requests
import json
from pprint import pprint
from os import getenv
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
import seaborn as sns
import matplotlib.pyplot as plt

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

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


def create_weather_dataframe(weather_json):
    """
    Convert Open-Meteo JSON response to a pandas DataFrame.

    Args:
        weather_json (dict): JSON response from get_weather_data function

    Returns:
        pandas.DataFrame: DataFrame with time as index and weather variables as columns
    """
    if not weather_json or "hourly" not in weather_json:
        print("Invalid weather data")
        return None

    # Extract hourly data
    hourly_data = weather_json["hourly"]

    # Create DataFrame from hourly data
    df = pd.DataFrame(hourly_data)

    # Convert time column to datetime
    df["time"] = pd.to_datetime(df["time"])

    # Set time as index for time series analysis
    df.set_index("time", inplace=True)

    # Store metadata as DataFrame attributes
    df.attrs["elevation"] = weather_json.get("elevation", None)
    df.attrs["latitude"] = weather_json.get("latitude", None)
    df.attrs["longitude"] = weather_json.get("longitude", None)
    df.attrs["timezone"] = weather_json.get("timezone", None)
    df.attrs["generation_time_ms"] = weather_json.get("generationtime_ms", None)

    # Store units information
    if "hourly_units" in weather_json:
        df.attrs["units"] = weather_json["hourly_units"]

    return df


def analyze_weather_dataframe(df):
    """
    Analyze the weather DataFrame and print statistics.

    Args:
        df (pandas.DataFrame): Weather DataFrame
    """
    print(f"\n{'='*50}")
    print("WEATHER DATA ANALYSIS")
    print(f"{'='*50}")

    # Basic info
    print(f"DataFrame Shape: {df.shape}")
    print(f"Date Range: {df.index.min()} to {df.index.max()}")
    print(
        f"Location: {df.attrs.get('latitude', 'N/A')}°N, {df.attrs.get('longitude', 'N/A')}°E"
    )
    print(f"Elevation: {df.attrs.get('elevation', 'N/A')}m")
    print(f"Timezone: {df.attrs.get('timezone', 'N/A')}")

    # Display first few rows
    print(f"\nFirst 10 rows:")
    print(df.head(10))

    # Rain analysis if rain column exists
    if "rain" in df.columns:
        print(f"\nRAIN ANALYSIS:")
        print(f"Total Rain: {df['rain'].sum():.2f} mm")
        print(f"Max Hourly Rain: {df['rain'].max():.2f} mm")
        print(f"Average Rain: {df['rain'].mean():.4f} mm/hour")
        print(f"Hours with Rain: {(df['rain'] > 0).sum()}")
        print(f"Units: {df.attrs.get('units', {}).get('rain', 'N/A')}")

        # Find rainy periods
        rainy_hours = df[df["rain"] > 0]
        if not rainy_hours.empty:
            print(f"\nRainy periods:")
            for idx, row in rainy_hours.iterrows():
                print(f"  {idx}: {row['rain']:.1f} mm")

    # Data types and info
    print(f"\nData Types:")
    print(df.dtypes)


def plot_weather_dataframe(df, city: str):
    """
    Create visualizations for the weather DataFrame.

    Args:
        df (pandas.DataFrame): Weather DataFrame
        city (str): Name of the city for the plot title
    """
    if "rain" not in df.columns:
        print("No rain data to plot")
        return

    # Seaborn plot
    plt.figure(figsize=(12, 6))
    sns.lineplot(data=df, x=df.index, y="rain", marker="o", markersize=4)
    plt.title(f"Rain Forecast for {city}", fontsize=14, fontweight="bold")
    plt.ylabel("Rain (mm)")
    plt.xlabel("Time")
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


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


def get_weather_data(lat: float, lon: float, WeatherVariable: str, forecastDays: int):
    """Fetch weather data using Open-Meteo API for given latitude and longitude."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": WeatherVariable,
        "forecast_days": forecastDays,
    }
    try:
        response = requests.get(url, params=params, timeout=5)
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


def main():
    # Get public IP address
    ip = get_ip()
    if not ip:
        print("Failed to get public IP")
        return

    # Get location data in JSON format
    loc = get_location(ip, "json")  # format possibilities: json, csv, xml
    print("\nJSON:")
    location_json = json.loads(loc if loc else "{}")
    pprint(location_json)
    location_data = location_json
    # Check if the request was successful
    if location_data.get("status") != "success":
        raise Exception("Location API request failed")

    # Extract latitude and longitude
    lat = location_data.get("lat")
    lon = location_data.get("lon")
    city = location_data.get("city")
    country = location_data.get("country")

    print(f"\nLocation: {city}, {country} (lat: {lat}, lon: {lon})")

    # Get real-time weather data
    weather = get_real_time_weather(lat, lon)
    if weather:
        print("\nReal-Time Weather Data:")
        pprint(weather)
    else:
        print("Failed to get weather data")

    # Fetch weather data
    response = get_weather_data(lat, lon, "rain", 16)
    if response:
        print("\nWeather Data (Open-Meteo):")
        pprint(response)

    weather_df = create_weather_dataframe(response)

    if weather_df is not None:
        # Analyze the DataFrame
        analyze_weather_dataframe(weather_df)

        # Create visualizations
        plot_weather_dataframe(weather_df, city)

        # Example of additional pandas operations
        print(f"\n{'='*50}")
        print("ADDITIONAL PANDAS OPERATIONS")
        print(f"{'='*50}")

        # Resample to daily data
        daily_stats = (
            weather_df["rain"].resample("D").agg(["sum", "max", "mean", "count"])
        )
        print("\nDaily Rain Statistics:")
        print(daily_stats)

        # Filter rainy hours
        rainy_hours = weather_df[weather_df["rain"] > 0]
        print(f"\nRainy Hours DataFrame ({len(rainy_hours)} hours):")
        print(rainy_hours)

    else:
        print("Failed to create DataFrame from weather data")


if __name__ == "__main__":
    main()
