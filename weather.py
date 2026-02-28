"""
weather.py
==========
Fetches forecast weather for each AFL venue using the Open-Meteo API.
Completely free — no API key required.

Weather is a genuine AFL prediction factor:
  - Rain increases contested marks, reduces scoring, favours underdogs
  - Strong wind affects kicking accuracy and goal-to-behind ratio
  - Extreme heat can cause fatigue in the final quarter
  - Marvel Stadium and Gabba have roofs — weather irrelevant for those
"""

import requests
from datetime import datetime


# ─── Venue coordinates & roof status ──────────────────────────────────────────
# Coordinates are the ground locations for weather lookup
VENUE_DATA = {
    # Victoria
    "MCG":                      {"lat": -37.8200, "lon": 144.9834, "roof": False, "city": "Melbourne"},
    "Marvel Stadium":           {"lat": -37.8165, "lon": 144.9475, "roof": True,  "city": "Melbourne"},
    "GMHBA Stadium":            {"lat": -38.1579, "lon": 144.3547, "roof": False, "city": "Geelong"},
    "Mars Stadium":             {"lat": -37.5622, "lon": 143.8503, "roof": False, "city": "Ballarat"},
    "Cazaly's Stadium":         {"lat": -16.9167, "lon": 145.7667, "roof": False, "city": "Cairns"},

    # New South Wales
    "SCG":                      {"lat": -33.8914, "lon": 151.2246, "roof": False, "city": "Sydney"},
    "Engie Stadium":            {"lat": -33.8471, "lon": 151.0635, "roof": False, "city": "Sydney"},
    "Giants Stadium":           {"lat": -33.8471, "lon": 150.9862, "roof": False, "city": "Sydney"},

    # Queensland
    "Gabba":                    {"lat": -27.4858, "lon": 153.0381, "roof": False, "city": "Brisbane"},
    "People First Stadium":     {"lat": -27.9834, "lon": 153.3639, "roof": False, "city": "Gold Coast"},

    # South Australia
    "Adelaide Oval":            {"lat": -34.9156, "lon": 138.5960, "roof": False, "city": "Adelaide"},

    # Western Australia
    "Optus Stadium":            {"lat": -31.9514, "lon": 115.8875, "roof": False, "city": "Perth"},

    # Northern Territory / Tasmania
    "TIO Stadium":              {"lat": -12.4139, "lon": 130.8865, "roof": False, "city": "Darwin"},
    "University of Tasmania Stadium": {"lat": -41.4332, "lon": 147.1441, "roof": False, "city": "Launceston"},
    "Blundstone Arena":         {"lat": -42.8826, "lon": 147.3468, "roof": False, "city": "Hobart"},

    # ACT
    "Manuka Oval":              {"lat": -35.3192, "lon": 149.1310, "roof": False, "city": "Canberra"},
}

# Alternative name mappings (Squiggle sometimes uses different names)
VENUE_ALIASES = {
    "Docklands":          "Marvel Stadium",
    "Etihad Stadium":     "Marvel Stadium",
    "Kardinia Park":      "GMHBA Stadium",
    "Carrara":            "People First Stadium",
    "Stadium Australia":  "Engie Stadium",
    "Spotless Stadium":   "Engie Stadium",
    "GIANTS Stadium":     "Giants Stadium",
    "Traeger Park":       "TIO Stadium",
    "Aurora Stadium":     "University of Tasmania Stadium",
}


def get_venue_info(venue_name):
    """Look up venue data, handling aliases."""
    # Try direct match first
    if venue_name in VENUE_DATA:
        return VENUE_DATA[venue_name], venue_name

    # Try alias
    canonical = VENUE_ALIASES.get(venue_name)
    if canonical and canonical in VENUE_DATA:
        return VENUE_DATA[canonical], canonical

    # Try partial match
    for name, data in VENUE_DATA.items():
        if name.lower() in venue_name.lower() or venue_name.lower() in name.lower():
            return data, name

    return None, venue_name


def get_weather_forecast(venue_name, game_date_str):
    """
    Fetch weather forecast for a venue on a given date.
    Uses Open-Meteo API — free, no key required.

    Returns a dict with weather info, or None if venue not found.
    """
    venue_info, canonical_name = get_venue_info(venue_name)

    if not venue_info:
        return {"venue": venue_name, "available": False, "reason": "Venue coordinates not found"}

    # Roofed stadiums — weather irrelevant
    if venue_info.get("roof"):
        return {
            "venue": canonical_name,
            "available": True,
            "roof": True,
            "summary": f"{canonical_name} has a roof — weather conditions will not affect play.",
            "impact": "None — covered venue"
        }

    lat = venue_info["lat"]
    lon = venue_info["lon"]

    # Parse game date
    try:
        game_date = datetime.strptime(game_date_str[:10], "%Y-%m-%d")
        date_str  = game_date.strftime("%Y-%m-%d")
    except Exception:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # Open-Meteo API call — free, no key needed
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude":           lat,
        "longitude":          lon,
        "daily":              [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "windspeed_10m_max",
            "precipitation_probability_max"
        ],
        "timezone":           "auto",
        "start_date":         date_str,
        "end_date":           date_str
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data     = response.json()
        daily    = data.get("daily", {})

        if not daily:
            return {"venue": canonical_name, "available": False, "reason": "No forecast data returned"}

        temp_max     = daily.get("temperature_2m_max",  [None])[0]
        temp_min     = daily.get("temperature_2m_min",  [None])[0]
        rain_mm      = daily.get("precipitation_sum",   [None])[0]
        wind_kph     = daily.get("windspeed_10m_max",   [None])[0]
        rain_prob    = daily.get("precipitation_probability_max", [None])[0]

        # Assess impact on game
        impact = assess_weather_impact(temp_max, rain_mm, wind_kph, rain_prob)

        # Build human-readable summary
        parts = []
        if temp_max is not None:
            parts.append(f"Max {temp_max:.0f}°C")
        if rain_mm is not None:
            parts.append(f"Rain: {rain_mm:.1f}mm ({rain_prob:.0f}% chance)")
        if wind_kph is not None:
            parts.append(f"Wind: {wind_kph:.0f} km/h")

        summary = ", ".join(parts) if parts else "Forecast unavailable"

        return {
            "venue":      canonical_name,
            "city":       venue_info.get("city", ""),
            "available":  True,
            "roof":       False,
            "date":       date_str,
            "temp_max":   temp_max,
            "temp_min":   temp_min,
            "rain_mm":    rain_mm,
            "rain_prob":  rain_prob,
            "wind_kph":   wind_kph,
            "summary":    summary,
            "impact":     impact
        }

    except Exception as e:
        return {"venue": canonical_name, "available": False, "reason": str(e)}


def assess_weather_impact(temp_max, rain_mm, wind_kph, rain_prob):
    """
    Assess how weather conditions will affect the game.
    Returns a plain-English impact description for the AI prompt.
    """
    factors = []

    # Rain impact
    rain_mm    = rain_mm or 0
    rain_prob  = rain_prob or 0

    if rain_mm > 10 or rain_prob > 70:
        factors.append(
            "HEAVY RAIN LIKELY — expect lower scores, more contested play, "
            "reduced effectiveness of high-marking forwards, "
            "tends to reduce the margin and benefit underdogs"
        )
    elif rain_mm > 3 or rain_prob > 40:
        factors.append(
            "SOME RAIN POSSIBLE — slightly slippery conditions, "
            "may reduce kicking accuracy"
        )

    # Wind impact
    wind_kph = wind_kph or 0
    if wind_kph > 50:
        factors.append(
            "STRONG WIND (>50 km/h) — significant advantage kicking with the wind, "
            "coin-toss to kick direction becomes important, "
            "expect lopsided quarter scores"
        )
    elif wind_kph > 30:
        factors.append(
            "MODERATE WIND (30-50 km/h) — some directional advantage, "
            "may affect goal-kicking accuracy"
        )

    # Heat impact
    temp_max = temp_max or 20
    if temp_max > 35:
        factors.append(
            "EXTREME HEAT (>35°C) — fatigue factor in Q4, "
            "teams with greater bench depth and fitness may have late advantage"
        )
    elif temp_max > 30:
        factors.append("WARM CONDITIONS (30-35°C) — minor fatigue factor in final quarter")

    if not factors:
        return "Conditions appear fine — weather unlikely to significantly affect the result"

    return " | ".join(factors)


def format_weather_for_ai(venue_name, game_date_str):
    """
    Fetch weather and format it as a string for injection into the AI prompt.
    """
    weather = get_weather_forecast(venue_name, game_date_str)

    if not weather.get("available"):
        return f"Weather data unavailable for {venue_name}."

    if weather.get("roof"):
        return weather["summary"]

    lines = [
        f"Forecast for {weather['venue']} on {weather['date']}: {weather['summary']}",
        f"Game impact assessment: {weather['impact']}"
    ]
    return "\n".join(lines)
