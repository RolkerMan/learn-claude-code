# Weather MCP Server

A Model Context Protocol server that provides weather data using the Open-Meteo API.

## Features

- **Current Weather**: Get real-time weather conditions for any city
- **Weather Forecast**: Get up to 7-day forecast with high/low temperatures
- **Weather Comparison**: Compare weather across multiple cities
- **Air Quality**: Get air quality index and pollutant levels

## Tools

### `get_current_weather`
Get current weather for a city.

**Parameters:**
- `city` (string): City name (e.g., "London", "New York", "Tokyo")

**Returns:** Temperature, humidity, wind speed, and conditions

### `get_forecast`
Get weather forecast for a city.

**Parameters:**
- `city` (string): City name
- `days` (integer, optional): Number of days (1-7, default 3)

**Returns:** Daily forecast with temperatures and precipitation probability

### `compare_weather`
Compare weather across multiple cities.

**Parameters:**
- `cities` (string): Comma-separated list of cities (max 5)

**Returns:** Side-by-side weather comparison

### `get_air_quality`
Get air quality index for a city.

**Parameters:**
- `city` (string): City name

**Returns:** AQI, PM2.5, PM10, ozone, and NO2 levels

## Installation

```bash
cd weather-mcp-server
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Testing

Test the server locally:

```bash
# Using MCP Inspector
npx @anthropics/mcp-inspector python3 weather_server.py

# Or test directly
python3 weather_server.py
```

## Register with Claude

Add to `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "weather": {
      "command": "python3",
      "args": ["D:\\WorkSpace\\learn-claude-code\\weather-mcp-server\\weather_server.py"]
    }
  }
}
```

**Note:** Update the path to match your actual location.

## Usage Examples

Once registered, Claude can use the tools:

```
You: What's the weather in Tokyo?
Claude: [uses get_current_weather tool]
→ Weather for Tokyo, Japan:
  Temperature: 18°C
  Humidity: 65%
  Wind Speed: 12 km/h
  Conditions: Partly cloudy

You: Compare weather in London, Paris, and Berlin
Claude: [uses compare_weather tool]
→ Weather Comparison:
------------------------------------------------------------
London, United Kingdom: 15°C, 78% humidity
Paris, France: 17°C, 72% humidity
Berlin, Germany: 14°C, 81% humidity

You: What's the air quality in Los Angeles?
Claude: [uses get_air_quality tool]
→ Air Quality for Los Angeles, United States:
  AQI (US): 85 - Moderate
  PM2.5: 12.5 µg/m³
  PM10: 18.2 µg/m³
  Ozone: 45.3 µg/m³
  NO2: 22.1 µg/m³
```

## API Details

This server uses **Open-Meteo API**, which is:
- Free to use
- No API key required
- No rate limits for reasonable use
- Reliable and well-maintained

## Error Handling

All tools include comprehensive error handling:
- City not found
- API timeout
- Invalid parameters
- Network errors

Errors are returned as descriptive messages for Claude to understand and relay to users.