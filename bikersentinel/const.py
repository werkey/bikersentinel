"""Constants for the BikerSentinel integration."""

DOMAIN = "bikersentinel"

# Configuration Keys (Internal keys used in storage)
CONF_HEIGHT = "height"
CONF_WEIGHT = "weight"
CONF_BIKE_TYPE = "bike_type"
CONF_EQUIPMENT = "equipment_level"
CONF_SENSITIVITY = "sensitivity"
CONF_RIDING_CONTEXT = "riding_context"
CONF_SENSOR_TEMP = "sensor_temp"
CONF_SENSOR_WIND = "sensor_wind"
CONF_SENSOR_RAIN = "sensor_rain"
CONF_WEATHER_ENTITY = "weather_entity"

# Trip Score Configuration
CONF_TRIP_ENABLED = "trip_score_enabled"
CONF_TRIP_HOME_WEATHER = "trip_home_weather"  # Weather at home (start location)
CONF_TRIP_OFFICE_WEATHER = "trip_office_weather"  # Weather at office (end location)
CONF_TRIP_DEPART_TIME = "trip_depart_time"
CONF_TRIP_RETURN_TIME = "trip_return_time"

# Malus Ratio Configuration (User-adjustable multipliers)
CONF_RAIN_RATIO = "rain_malus_ratio"
CONF_FOG_RATIO = "fog_malus_ratio"
CONF_CLOUDY_RATIO = "cloudy_malus_ratio"
CONF_COLD_RATIO = "cold_malus_ratio"
CONF_HOT_RATIO = "hot_malus_ratio"
CONF_WIND_RATIO = "wind_malus_ratio"
CONF_HUMIDITY_RATIO = "humidity_malus_ratio"
CONF_NIGHT_RATIO = "night_malus_ratio"
CONF_ROAD_STATE_RATIO = "road_state_malus_ratio"

# Note: Night Mode, Precipitation History, Temperature/Humidity Trends, and Solar Blindness
# are now always active and internal - no user toggles needed

# Defaults ( Metric System )
DEFAULT_HEIGHT_CM = 175
DEFAULT_WEIGHT_KG = 80
DEFAULT_BIKE_TYPE = "Roadster"
DEFAULT_EQUIPMENT = "Standard"
DEFAULT_SENSITIVITY = 3  # 1=Low (Viking), 3=Normal, 5=High (Cold)
DEFAULT_RIDING_CONTEXT = "road"

# Malus Ratio Defaults (1.0 = standard sensitivity)
DEFAULT_RAIN_RATIO = 1.0
DEFAULT_FOG_RATIO = 1.0
DEFAULT_CLOUDY_RATIO = 1.0
DEFAULT_COLD_RATIO = 1.0
DEFAULT_HOT_RATIO = 1.0
DEFAULT_WIND_RATIO = 1.0
DEFAULT_HUMIDITY_RATIO = 1.0
DEFAULT_NIGHT_RATIO = 1.0
DEFAULT_ROAD_STATE_RATIO = 1.0

# Available Selections (Internal values)
# Note: These values are stored in config, not displayed directly if translated
MACHINE_TYPES = ["Roadster", "Sportive", "GT", "Trail", "Custom", "125cc"]
EQUIPMENT_LEVELS = ["Standard", "Winter", "Heated"]

# Riding context / Average speed (km/h) by context
RIDING_CONTEXTS = {
    "urban": 30,        # City riding average
    "road": 80,         # Road riding average
    "highway": 130      # Highway riding average
}

# Aerodynamic Protection Coefficients (Lower factor = Better protection)
PROTECTION_COEFS = {
    "Roadster": 1.2,   # Full wind exposure
    "Sportive": 1.0,   # Partial fairing
    "GT": 0.7,         # Full fairing + windshield
    "Trail": 0.9,      # Upright but handguards/screen
    "Custom": 1.1,     # Low center of gravity but open
    "125cc": 1.05      # Lower average speeds
}

# Equipment Efficiency Factors (Reduces cold impact)
# 1.0 = No reduction, 0.3 = Massive reduction (Heated gear)
EQUIPMENT_COEFS = {
    "Standard": 1.0,
    "Winter": 0.6,
    "Heated": 0.3
}

# Night Mode Visibility Penalty (based on solar elevation)
# Solar elevation ranges from -18° (astronomical twilight) to +90° (zenith)
# Malus increases as sun goes down
NIGHT_MODE_MALUS = {
    "day": 0.0,              # Sun above 10° - Full visibility
    "twilight": -1.5,        # Sun between -6° and 10° - Reduced visibility
    "civil_twilight": -3.0,  # Sun between -6° and 0° - Low visibility
    "night": -5.0            # Sun below -6° - Poor visibility
}

# Precipitation History window (hours) for correlation
PRECIP_HISTORY_WINDOW = 24  # Track 24-hour history

# Road State Conditions (Precipitation-based)
# Thresholds for inferring road surface conditions from rainfall
ROAD_STATE_THRESHOLDS = {
    "dry": (0, 0.0),           # 0 - 0 mm
    "damp": (0.1, 5.0),        # 0.1 - 5 mm
    "wet": (5.0, 10.0),        # 5 - 10 mm
    "sludge": (10.0, 99.0),    # 10+ mm (with normal temp)
    "icy": (10.0, 99.0),       # 10+ mm (with temp < 0°C)
}

# Road State Malus Values (applied to score)
ROAD_STATE_MALUS = {
    "dry": 0.0,
    "damp": -1.0,
    "wet": -3.0,
    "sludge": -6.0,
    "icy": -8.0,
    "unknown": 0.0,
}

# Temperature Trend Detection
TEMP_HISTORY_WINDOW = 6  # Track last 6 readings for trend analysis
TEMP_DROP_THRESHOLD = 5.0  # Sudden drop > 5°C = risk of icing
TEMP_TREND_MALUS = {
    "dropping": -2.0,  # Temperature falling rapidly
    "stable": 0.0,     # Temperature stable
    "rising": 0.5,     # Temperature rising (safer)
}

# Humidity Impact on Visibility
HUMIDITY_THRESHOLDS = {
    "low": (0, 30),         # Good visibility
    "moderate": (30, 70),   # Normal visibility
    "high": (70, 100),      # Reduced visibility (fog risk)
}

HUMIDITY_MALUS = {
    "low": 0.0,
    "moderate": 0.0,
    "high": -1.5,  # High humidity increases fog risk
}

# Solar Blindness (Glare Risk Detection - Internal Feature, Always Active)
# Based on sun azimuth (0° = N, 90° = E, 180° = S, 270° = W)
SOLAR_BLINDNESS_THRESHOLD = 60  # degrees from front azimuth (90-270°)
SOLAR_BLINDNESS_MALUS = {
    "safe": 0.0,           # Sun not in glare zone
    "caution": -1.0,       # Sun approaching glare angle
    "warning": -2.5,       # Sun in prime glare zone
}