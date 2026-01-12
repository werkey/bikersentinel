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

# Defaults ( Metric System )
DEFAULT_HEIGHT_CM = 175
DEFAULT_WEIGHT_KG = 80
DEFAULT_BIKE_TYPE = "Roadster"
DEFAULT_EQUIPMENT = "Standard"
DEFAULT_SENSITIVITY = 3  # 1=Low (Viking), 3=Normal, 5=High (Cold)
DEFAULT_RIDING_CONTEXT = "road"

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