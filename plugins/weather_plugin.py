"""
Weather Plugin for JARVIS
Provides weather information using Open-Meteo API (free, no API key required)
"""

import logging
from typing import Dict, Callable
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from modules.plugin_system import JARVISPlugin

logger = logging.getLogger(__name__)


class WeatherPlugin(JARVISPlugin):
    """
    Weather information plugin
    
    Features:
    - Current weather
    - Forecast
    - No API key required (uses Open-Meteo)
    """
    
    name = "weather"
    version = "1.0.0"
    description = "Weather information (free, no API key)"
    author = "JARVIS Team"
    
    # No external dependencies required
    required_packages = ["requests"]
    
    def __init__(self):
        super().__init__()
        self.default_location = "London"  # Default to UK
        self.default_lat = 51.5074
        self.default_lon = -0.1278
    
    def initialize(self) -> bool:
        """Initialize weather plugin"""
        try:
            # Load default location from config if exists
            config_file = Path.home() / "jarvis" / "config" / "weather_config.json"
            
            if config_file.exists():
                import json
                with open(config_file) as f:
                    config = json.load(f)
                self.default_location = config.get("location", "London")
                self.default_lat = config.get("lat", 51.5074)
                self.default_lon = config.get("lon", -0.1278)
            
            logger.info(f"Weather plugin initialized (default: {self.default_location})")
            return True
        except Exception as e:
            logger.error(f"Weather plugin initialization failed: {str(e)}")
            return False
    
    def get_tools(self) -> Dict[str, Callable]:
        """Return weather tools"""
        return {
            "current": self.get_current_weather,
            "forecast": self.get_forecast,
            "set_location": self.set_location,
            "time": self.get_time  # Added time tool
        }
    
    def get_time(self) -> Dict:
        """
        Get current time
        
        Returns:
            Current time information
        """
        from datetime import datetime
        
        now = datetime.now()
        
        return {
            "success": True,
            "time": now.strftime("%H:%M:%S"),
            "date": now.strftime("%A, %B %d, %Y"),
            "timezone": "Local"
        }
    
    def get_current_weather(self, location: str = None) -> Dict:
        """
        Get current weather for a location
        
        Args:
            location: City name (optional, uses default if not provided)
            
        Returns:
            {"success": bool, "temperature": float, "conditions": str, ...}
        """
        try:
            import requests
            
            # Get coordinates for location
            if location:
                lat, lon = self._geocode(location)
            else:
                lat, lon = self.default_lat, self.default_lon
                location = self.default_location
            
            if lat is None:
                return {"success": False, "error": f"Could not find location: {location}"}
            
            # Get weather from Open-Meteo
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current_weather": True
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            current = data.get("current_weather", {})
            
            # Map weather codes to descriptions
            weather_codes = {
                0: "Clear sky",
                1: "Mainly clear",
                2: "Partly cloudy",
                3: "Overcast",
                45: "Foggy",
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
                96: "Thunderstorm with hail",
                99: "Thunderstorm with heavy hail"
            }
            
            code = current.get("wcode", 0)
            conditions = weather_codes.get(code, "Unknown")
            
            return {
                "success": True,
                "location": location,
                "temperature": current.get("temperature", 0),
                "temperature_unit": "°C",
                "conditions": conditions,
                "wind_speed": current.get("windspeed", 0),
                "wind_unit": "km/h"
            }
        
        except Exception as e:
            logger.error(f"Weather fetch failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_forecast(self, days: int = 3, location: str = None) -> Dict:
        """
        Get weather forecast
        
        Args:
            days: Number of days (1-7)
            location: City name
            
        Returns:
            {"success": bool, "forecast": List[dict]}
        """
        try:
            import requests
            
            # Get coordinates
            if location:
                lat, lon = self._geocode(location)
            else:
                lat, lon = self.default_lat, self.default_lon
                location = self.default_location
            
            if lat is None:
                return {"success": False, "error": f"Could not find location: {location}"}
            
            # Get forecast
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": ["temperature_2m_max", "temperature_2m_min", "weathercode"],
                "forecast_days": min(days, 7)
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            daily = data.get("daily", {})
            dates = daily.get("time", [])
            max_temps = daily.get("temperature_2m_max", [])
            min_temps = daily.get("temperature_2m_min", [])
            codes = daily.get("weathercode", [])
            
            forecast = []
            weather_codes = {
                0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Cloudy",
                45: "Foggy", 61: "Rain", 63: "Rain", 65: "Heavy rain",
                71: "Snow", 73: "Snow", 75: "Heavy snow", 95: "Thunderstorm"
            }
            
            for i in range(len(dates)):
                forecast.append({
                    "date": dates[i],
                    "max_temp": max_temps[i] if i < len(max_temps) else 0,
                    "min_temp": min_temps[i] if i < len(min_temps) else 0,
                    "conditions": weather_codes.get(codes[i] if i < len(codes) else 0, "Unknown")
                })
            
            return {
                "success": True,
                "location": location,
                "forecast": forecast
            }
        
        except Exception as e:
            logger.error(f"Forecast fetch failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def set_location(self, location: str) -> Dict:
        """
        Set default location for weather queries
        
        Args:
            location: City name
            
        Returns:
            {"success": bool, "message": str}
        """
        lat, lon = self._geocode(location)
        
        if lat is None:
            return {"success": False, "error": f"Could not find location: {location}"}
        
        self.default_location = location
        self.default_lat = lat
        self.default_lon = lon
        
        # Save to config
        config_file = Path.home() / "jarvis" / "config" / "weather_config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        import json
        with open(config_file, 'w') as f:
            json.dump({
                "location": location,
                "lat": lat,
                "lon": lon
            }, f, indent=2)
        
        return {
            "success": True,
            "message": f"Default location set to {location}"
        }
    
    def _geocode(self, location: str) -> tuple:
        """
        Get coordinates for a location name
        
        Returns:
            (lat, lon) or (None, None) if not found
        """
        try:
            import requests
            
            url = "https://geocoding-api.open-meteo.com/v1/search"
            params = {
                "name": location,
                "count": 1,
                "language": "en",
                "format": "json"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            if results:
                return results[0]["latitude"], results[0]["longitude"]
            
            return None, None
        
        except Exception as e:
            logger.error(f"Geocoding failed: {str(e)}")
            return None, None
    
    def get_system_prompt_addition(self) -> str:
        """Add weather capabilities to system prompt"""
        return """**Weather Tools:**

- `weather.current(location)` - Get current weather
- `weather.forecast(days, location)` - Get forecast (1-7 days)
- `weather.set_location(city)` - Set default location

Examples:
- "What's the weather in London?"
- "Get the 3-day forecast for Manchester"
- "Set my location to Birmingham"
- "Is it raining outside?"
"""
    
    def cleanup(self):
        """Cleanup"""
        logger.info("Weather plugin cleanup complete")
