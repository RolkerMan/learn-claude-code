#!/usr/bin/env python3
"""Test script for weather MCP server tools"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the tool functions directly
from weather_server import get_current_weather, get_forecast, compare_weather, get_air_quality


async def test_tools():
    """Test all weather tools directly"""
    
    print("=" * 60)
    print("Testing Weather MCP Server Tools")
    print("=" * 60)
    
    # Test 1: Current weather
    print("\n1. Testing get_current_weather('London')...")
    result = await get_current_weather("London")
    print(result)
    
    # Test 2: Forecast
    print("\n2. Testing get_forecast('Tokyo', days=3)...")
    result = await get_forecast("Tokyo", days=3)
    print(result)
    
    # Test 3: Compare weather
    print("\n3. Testing compare_weather('New York,Los Angeles,Chicago')...")
    result = await compare_weather("New York,Los Angeles,Chicago")
    print(result)
    
    # Test 4: Air quality
    print("\n4. Testing get_air_quality('Paris')...")
    result = await get_air_quality("Paris")
    print(result)
    
    # Test 5: Error handling
    print("\n5. Testing error handling with invalid city...")
    result = await get_current_weather("ThisCityDoesNotExist12345")
    print(result)
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_tools())