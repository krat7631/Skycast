import os
import requests
import pandas as pd

# Your OpenCage API Key
GEOCODING_API_KEY = "5b3cc3749ba6441b8e1d771f52cea6f1"

def get_lat_lon(city, state, country):
    # Make state optional (more flexible for global cities)
    query_parts = [city, state, country]
    query = ",".join([part for part in query_parts if part])  # skip empty state
    url = f"https://api.opencagedata.com/geocode/v1/json?q={query}&key={GEOCODING_API_KEY}"

    response = requests.get(url, timeout=10)
    data = response.json()

    if data.get("results"):
        lat = data["results"][0]["geometry"]["lat"]
        lon = data["results"][0]["geometry"]["lng"]
        return lat, lon
    else:
        raise Exception(f"❌ Geocoding failed for: {query}")

def fetch_forecast_data(city, state, country):
    lat, lon = get_lat_lon(city, state, country)
    print(f"📍 Coordinates fetched: {lat}, {lon}")

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_min,temperature_2m_max,precipitation_sum,wind_speed_10m_max,cloud_cover_mean"
        f"&forecast_days=16"
        f"&timezone=auto"
    )

    response = requests.get(url, timeout=10)
    data = response.json()

    print("✅ Open-Meteo API response keys:", data.keys())

    # Check if forecast data exists
    if "daily" not in data or not data["daily"].get("time"):
        raise Exception(f"❌ Open-Meteo returned no forecast data for {city}, {country}")

    df = pd.DataFrame({
        "date": data["daily"]["time"],
        "temperature_min": data["daily"]["temperature_2m_min"],
        "temperature_max": data["daily"]["temperature_2m_max"],
        "precipitation": data["daily"]["precipitation_sum"],
        "wind_speed": data["daily"]["wind_speed_10m_max"],
        "cloud_cover": data["daily"]["cloud_cover_mean"]
    })

    # Use clean file names
    city_clean = city.replace(" ", "_")
    country_clean = country.replace(" ", "_")

    os.makedirs("data", exist_ok=True)
    filename = f"data/{city_clean}_{country_clean}.csv"
    df.to_csv(filename, index=False)
    print(f"✅ Forecast data saved to {filename}")

    return filename

# Test manually if needed
if __name__ == "__main__":
    fetch_forecast_data("Vadodara", "", "India")  # test without state
