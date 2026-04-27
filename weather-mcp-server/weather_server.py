#!/usr/bin/env python3
"""
Weather MCP Server
Provides weather data using Open-Meteo API (free, no API key required)
"""

import asyncio
import json
import urllib.request
import urllib.parse
from mcp.server.fastmcp import FastMCP

# Create FastMCP instance
mcp = FastMCP("weather-server")


def fetch_json(url: str) -> dict:
    """Fetch JSON data from URL."""
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode())


def geocode_city(city: str) -> dict:
    """Get coordinates for a city name."""
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1"
    data = fetch_json(url)
    
    if not data.get("results"):
        raise ValueError(f"City '{city}' not found")
    
    result = data["results"][0]
    return {
        "name": result["name"],
        "country": result.get("country", "Unknown"),
        "latitude": result["latitude"],
        "longitude": result["longitude"],
    }


@mcp.tool()
async def get_current_weather(city: str) -> str:
    """Get current weather for a city.

    Args:
        city: City name (e.g., "London", "New York", "Tokyo")
    
    Returns:
        Current temperature, humidity, wind speed, and conditions
    """
    try:
        # Get coordinates
        location = geocode_city(city)
        
        # Get weather data
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={location['latitude']}"
            f"&longitude={location['longitude']}"
            f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
            f"&timezone=auto"
        )
        data = fetch_json(url)
        
        current = data["current"]
        weather_codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            95: "Thunderstorm",
        }
        
        condition = weather_codes.get(current["weather_code"], "Unknown")
        
        return (
            f"Weather for {location['name']}, {location['country']}:\n"
            f"  Temperature: {current['temperature_2m']}°C\n"
            f"  Humidity: {current['relative_humidity_2m']}%\n"
            f"  Wind Speed: {current['wind_speed_10m']} km/h\n"
            f"  Conditions: {condition}"
        )
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error fetching weather: {str(e)}"


@mcp.tool()
async def get_forecast(city: str, days: int = 3) -> str:
    """Get weather forecast for a city.

    Args:
        city: City name (e.g., "London", "New York", "Tokyo")
        days: Number of days (1-7, default 3)
    
    Returns:
        Daily weather forecast with high/low temperatures
    """
    try:
        # Validate days
        days = max(1, min(7, days))
        
        # Get coordinates
        location = geocode_city(city)
        
        # Get forecast data
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={location['latitude']}"
            f"&longitude={location['longitude']}"
            f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            f"&timezone=auto"
            f"&forecast_days={days}"
        )
        data = fetch_json(url)
        
        weather_codes = {
            0: "Clear", 1: "Clear", 2: "Cloudy", 3: "Overcast",
            45: "Fog", 48: "Fog",
            51: "Drizzle", 53: "Drizzle", 55: "Drizzle",
            61: "Rain", 63: "Rain", 65: "Rain",
            71: "Snow", 73: "Snow", 75: "Snow",
            95: "Storm",
        }
        
        lines = [f"{days}-Day Forecast for {location['name']}, {location['country']}:\n"]
        
        daily = data["daily"]
        for i, date in enumerate(daily["time"]):
            condition = weather_codes.get(daily["weather_code"][i], "Unknown")
            high = daily["temperature_2m_max"][i]
            low = daily["temperature_2m_min"][i]
            precip = daily["precipitation_probability_max"][i]
            
            lines.append(
                f"  {date}: {condition}, {low}°C to {high}°C, "
                f"{precip}% chance of rain"
            )
        
        return "\n".join(lines)
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error fetching forecast: {str(e)}"


@mcp.tool()
async def compare_weather(cities: str) -> str:
    """Compare current weather across multiple cities.

    Args:
        cities: Comma-separated list of cities (e.g., "London,Paris,Berlin")
    
    Returns:
        Side-by-side comparison of weather conditions
    """
    try:
        city_list = [c.strip() for c in cities.split(",") if c.strip()]
        
        if not city_list:
            return "Error: No cities provided"
        
        if len(city_list) > 5:
            return "Error: Maximum 5 cities allowed for comparison"
        
        results = []
        for city in city_list:
            try:
                location = geocode_city(city)
                url = (
                    f"https://api.open-meteo.com/v1/forecast"
                    f"?latitude={location['latitude']}"
                    f"&longitude={location['longitude']}"
                    f"&current=temperature_2m,relative_humidity_2m,weather_code"
                    f"&timezone=auto"
                )
                data = fetch_json(url)
                current = data["current"]
                
                results.append({
                    "city": location["name"],
                    "country": location["country"],
                    "temp": current["temperature_2m"],
                    "humidity": current["relative_humidity_2m"],
                })
            except Exception as e:
                results.append({
                    "city": city,
                    "error": str(e),
                })
        
        # Format output
        lines = ["Weather Comparison:"]
        lines.append("-" * 60)
        for r in results:
            if "error" in r:
                lines.append(f"{r['city']}: Error - {r['error']}")
            else:
                lines.append(
                    f"{r['city']}, {r['country']}: "
                    f"{r['temp']}°C, {r['humidity']}% humidity"
                )
        
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def get_air_quality(city: str) -> str:
    """Get air quality index for a city.

    Args:
        city: City name (e.g., "London", "New York", "Tokyo")
    
    Returns:
        Air quality index and pollutant levels
    """
    try:
        # Get coordinates
        location = geocode_city(city)
        
        # Get air quality data
        url = (
            f"https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={location['latitude']}"
            f"&longitude={location['longitude']}"
            f"&current=us_aqi,pm10,pm2_5,ozone,nitrogen_dioxide"
            f"&timezone=auto"
        )
        data = fetch_json(url)
        
        current = data["current"]
        
        # AQI categories (US EPA standard)
        aqi = current["us_aqi"]
        if aqi <= 50:
            category = "Good"
        elif aqi <= 100:
            category = "Moderate"
        elif aqi <= 150:
            category = "Unhealthy for Sensitive Groups"
        elif aqi <= 200:
            category = "Unhealthy"
        elif aqi <= 300:
            category = "Very Unhealthy"
        else:
            category = "Hazardous"
        
        return (
            f"Air Quality for {location['name']}, {location['country']}:\n"
            f"  AQI (US): {aqi} - {category}\n"
            f"  PM2.5: {current['pm2_5']:.1f} µg/m³\n"
            f"  PM10: {current['pm10']:.1f} µg/m³\n"
            f"  Ozone: {current['ozone']:.1f} µg/m³\n"
            f"  NO2: {current['nitrogen_dioxide']:.1f} µg/m³"
        )
    except Exception as e:
        return f"Error fetching air quality: {str(e)}"


if __name__ == "__main__":
    mcp.run()