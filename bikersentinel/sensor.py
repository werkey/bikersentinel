"""Sensor platform for BikerSentinel."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    PROTECTION_COEFS,
    EQUIPMENT_COEFS,
    RIDING_CONTEXTS,
    NIGHT_MODE_MALUS,
    PRECIP_HISTORY_WINDOW,
    TEMP_HISTORY_WINDOW,
    TEMP_DROP_THRESHOLD,
    TEMP_TREND_MALUS,
    HUMIDITY_THRESHOLDS,
    HUMIDITY_MALUS,
    CONF_HEIGHT,
    CONF_WEIGHT,
    CONF_BIKE_TYPE,
    CONF_EQUIPMENT,
    CONF_SENSITIVITY,
    CONF_RIDING_CONTEXT,
    CONF_SENSOR_TEMP,
    CONF_SENSOR_WIND,
    CONF_SENSOR_RAIN,
    CONF_WEATHER_ENTITY,
    CONF_TRIP_ENABLED,
    CONF_TRIP_WEATHER_START,
    CONF_TRIP_WEATHER_END,
    CONF_TRIP_DEPART_TIME,
    CONF_TRIP_RETURN_TIME,
    CONF_NIGHT_MODE_ENABLED,
    CONF_PRECIP_HISTORY_ENABLED,
    CONF_TEMP_HUMIDITY_TRENDS_ENABLED,
    DEFAULT_HEIGHT_CM,
    DEFAULT_WEIGHT_KG,
    DEFAULT_BIKE_TYPE,
    DEFAULT_EQUIPMENT,
    DEFAULT_SENSITIVITY,
    DEFAULT_RIDING_CONTEXT,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BikerSentinel sensors."""
    
    # Retrieve config data with fallbacks (English keys)
    height = entry.data.get(CONF_HEIGHT) or DEFAULT_HEIGHT_CM
    weight = entry.data.get(CONF_WEIGHT) or DEFAULT_WEIGHT_KG
    bike_type = entry.data.get(CONF_BIKE_TYPE, DEFAULT_BIKE_TYPE)
    equipment = entry.data.get(CONF_EQUIPMENT, DEFAULT_EQUIPMENT)
    sensitivity = entry.data.get(CONF_SENSITIVITY, DEFAULT_SENSITIVITY)
    riding_context = entry.data.get(CONF_RIDING_CONTEXT, DEFAULT_RIDING_CONTEXT)
    night_mode_enabled = entry.data.get(CONF_NIGHT_MODE_ENABLED, True)
    precip_history_enabled = entry.data.get(CONF_PRECIP_HISTORY_ENABLED, True)
    trip_enabled = entry.data.get(CONF_TRIP_ENABLED, False)
    temp_humidity_enabled = entry.data.get(CONF_TEMP_HUMIDITY_TRENDS_ENABLED, False)

    # Create the Score entity and store in runtime data for Status/Reasoning
    score_entity = BikerSentinelScore(hass, entry, height, weight, bike_type, equipment, sensitivity, riding_context)
    runtime_data = {"score_entity": score_entity}

    # Build list of entities to add
    entities = [
        score_entity,
        BikerSentinelStatus(hass, entry),
        BikerSentinelReasoning(hass, entry),
    ]
    
    # Add optional features if enabled
    if night_mode_enabled:
        entities.append(BikerSentinelNightMode(hass, entry))
    
    if precip_history_enabled:
        precip_entity = BikerSentinelPrecipitationHistory(hass, entry)
        entities.append(precip_entity)
        runtime_data["precip_entity"] = precip_entity
    
    if trip_enabled:
        entities.append(BikerSentinelTripScore(hass, entry))
    
    if temp_humidity_enabled:
        entities.append(BikerSentinelTemperatureTrend(hass, entry))
        entities.append(BikerSentinelHumidityTrend(hass, entry))

    entry.runtime_data = runtime_data
    async_add_entities(entities, True)


class BikerSentinelScore(SensorEntity):
    """Representation of the main BikerSentinel Score."""

    _attr_has_entity_name = True
    _attr_translation_key = "score"
    _attr_native_unit_of_measurement = "/10"
    _attr_icon = "mdi:motorbike"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, entry, height, weight, bike_type, equipment, sensitivity, riding_context):
        """Initialize the score sensor."""
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_score"
        
        # Internal attribute to store reasoning list
        self._attr_extra_state_attributes = {"reasons": []}
        
        self._ent_temp = entry.data.get(CONF_SENSOR_TEMP)
        self._ent_wind = entry.data.get(CONF_SENSOR_WIND)
        self._ent_rain = entry.data.get(CONF_SENSOR_RAIN)
        self._ent_weather = entry.data.get(CONF_WEATHER_ENTITY)
        self._riding_context = riding_context
        
        # Load Coefficients
        self._coef = PROTECTION_COEFS.get(bike_type, 1.2)
        self._equip_coef = EQUIPMENT_COEFS.get(equipment, 1.0)
        
        # Calculate Surface Area using DuBois Formula (more accurate than linear approximation)
        # BSA (m²) = 0.007184 * height(cm)^0.725 * weight(kg)^0.425
        # Simplified for computational efficiency: approximate to frontal surface
        import math
        self._surface = 0.007184 * math.pow(height, 0.725) * math.pow(weight, 0.425)
        
        # Sensitivity Factor:
        # 3 (Normal) -> 1.0
        # 1 (Viking) -> 0.8 (Reduces cold impact)
        # 5 (Sensitive) -> 1.2 (Increases cold impact)
        self._sens_factor = 1.0 + ((sensitivity - 3) * 0.1)

    @property
    def native_value(self):
        """Calculate and return the score."""
        reasons = [] # Reset reasons list
        
        try:
            s_temp = self._hass.states.get(self._ent_temp)
            s_wind = self._hass.states.get(self._ent_wind)
            s_rain = self._hass.states.get(self._ent_rain)
            
            # Check for availability
            if not s_temp or not s_wind or not s_rain:
                return None
            if s_temp.state in ["unknown", "unavailable"] or s_wind.state in ["unknown", "unavailable"]:
                 return None

            t = float(s_temp.state)
            v = float(s_wind.state)
            p = float(s_rain.state) if s_rain.state not in ["unknown", "unavailable"] else 0.0
            
            # Weather entity check
            weather_state = "clear"
            if self._ent_weather:
                w_state = self._hass.states.get(self._ent_weather)
                if w_state and w_state.state not in ["unknown", "unavailable"]:
                    weather_state = w_state.state

            # --- ALGORITHM ---

            # 1. SAFETY VETOS (Immediate 0)
            # Translation keys are handled by the frontend, but we store raw keys in reasons if needed
            if weather_state in ["snowy", "snowy-rainy", "hail", "lightning-rainy"]:
                self._attr_extra_state_attributes["reasons"] = ["Dangerous Weather"]
                return 0.0
            if t < 1:
                self._attr_extra_state_attributes["reasons"] = ["Ice Risk"]
                return 0.0
            if v > 85:
                self._attr_extra_state_attributes["reasons"] = ["Storm Winds"]
                return 0.0

            score = 10.0

            # 2. VISIBILITY (Fog)
            if weather_state == "fog":
                score -= 3.0
                reasons.append("Fog (-3)")

            # 2b. NIGHT MODE & VISIBILITY (Solar elevation)
            night_mode_enabled = self._entry.data.get(CONF_NIGHT_MODE_ENABLED, True)
            if night_mode_enabled:
                try:
                    sun_state = self._hass.states.get("sun.sun")
                    if sun_state:
                        elevation = float(sun_state.attributes.get("elevation", 10))
                        
                        # Determine visibility status and apply malus
                        if elevation > 10:
                            night_malus = NIGHT_MODE_MALUS.get("day", 0.0)
                        elif elevation > 0:
                            night_malus = NIGHT_MODE_MALUS.get("twilight", 0.0)
                        elif elevation > -6:
                            night_malus = NIGHT_MODE_MALUS.get("civil_twilight", 0.0)
                        else:
                            night_malus = NIGHT_MODE_MALUS.get("night", 0.0)
                        
                        if night_malus < 0:
                            score += night_malus  # night_malus is negative, so we add it
                            reasons.append(f"Night Mode ({night_malus:.1f})")
                except Exception:
                    pass  # Silently skip if sun.sun is not available

            # 3. WINDCHILL (Thermal Comfort)
            # Dynamic wind speed considering riding context (configured by user)
            # Defines average speed in typical riding conditions
            riding_speed = RIDING_CONTEXTS.get(self._riding_context, 80)
            
            # Total wind effect = weather wind + forward motion wind
            # t_felt considers total wind + bike protection
            total_wind = v + (riding_speed * 0.1)  # 10% of riding speed contributes to perceived wind
            t_felt = t - (total_wind * 0.2 * self._coef)
            
            if t_felt < 15:
                # Formula: DeltaT * Severity * Surface * Equipment * Sensitivity
                raw_malus = (15 - t_felt) * 0.2 * self._surface
                final_malus = raw_malus * self._equip_coef * self._sens_factor
                
                score -= final_malus
                reasons.append(f"Felt Temp {t_felt:.1f}C (-{final_malus:.1f})")

            # 4. WIND STABILITY (Lateral Wind)
            if v > 35:
                malus_wind = (v - 35) * 0.15 * self._coef
                score -= malus_wind
                reasons.append(f"Wind Gusts {v}km/h (-{malus_wind:.1f})")

            # 5. RAIN (Road Condition)
            if p > 0:
                score -= 3.0
                reasons.append(f"Rain {p}mm (-3)")

            # 6. PRECIPITATION HISTORY & ROAD STATE (Enhanced condition analysis)
            precip_history_enabled = self._entry.data.get(CONF_PRECIP_HISTORY_ENABLED, False)
            if precip_history_enabled:
                try:
                    # Find the PrecipitationHistory entity in entry runtime_data
                    precip_entity = self._entry.runtime_data.get("precip_entity")
                    if precip_entity:
                        road_state = precip_entity.extra_state_attributes.get("road_state", "unknown")
                        road_malus = precip_entity.extra_state_attributes.get("road_malus", 0.0)
                        
                        if road_malus < 0:  # Only apply negative malus
                            score += road_malus
                            reasons.append(f"Road {road_state.capitalize()} ({road_malus:.1f})")
                except Exception as e:
                    _LOGGER.debug("Could not apply precipitation history malus: %s", e)

            # Update attribute for the Reasoning sensor to read
            self._attr_extra_state_attributes["reasons"] = reasons if reasons else ["Perfect Conditions"]

            return round(max(0, min(10, score)), 1)
            
        except Exception as e:
            _LOGGER.error("Error calculating BikerSentinel score: %s", e)
            return None


class BikerSentinelStatus(SensorEntity):
    """Status Text Sensor (Returns translation keys)."""

    _attr_has_entity_name = True
    _attr_translation_key = "status"
    _attr_icon = "mdi:shield-check"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["optimal", "favorable", "degraded", "critical", "dangerous", "analyzing", "error"]

    def __init__(self, hass, entry):
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_status"

    @property
    def native_value(self):
        """Get status from Score entity stored in runtime_data."""
        try:
            score_entity = self._entry.runtime_data.get("score_entity")
            if not score_entity:
                return "analyzing"
            
            # Access Score's native_value directly
            score = score_entity.native_value
            if score is None:
                return "analyzing"
            
            s = float(score)
            if s >= 9:
                return "optimal"
            if s >= 7:
                return "favorable"
            if s >= 5:
                return "degraded"
            if s >= 3:
                return "critical"
            return "dangerous"
        except Exception:
            return "error"


class BikerSentinelReasoning(SensorEntity):
    """Reasoning Text Sensor (Explains the score)."""

    _attr_has_entity_name = True
    _attr_translation_key = "reasoning"
    _attr_icon = "mdi:text-box-outline"

    def __init__(self, hass, entry):
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_reasoning"

    @property
    def native_value(self):
        """Reads the 'reasons' attribute from the Score entity stored in runtime_data."""
        try:
            score_entity = self._entry.runtime_data.get("score_entity")
            if not score_entity:
                return "Initializing..."
            
            # Access the Score's attributes directly
            reasons = score_entity.extra_state_attributes.get("reasons", [])
            
            if not reasons:
                return "RAS"
            return ", ".join(reasons)
        except Exception as e:
            _LOGGER.error("Error reading BikerSentinel reasoning: %s", e)
            return "Error"


class BikerSentinelNightMode(SensorEntity):
    """Night Mode & Azimuth visibility penalty sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "night_mode"
    _attr_icon = "mdi:weather-night"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["day", "twilight", "civil_twilight", "night"]
    _attr_unit_of_measurement = None

    def __init__(self, hass, entry):
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_night_mode"

    @property
    def native_value(self):
        """Calculate visibility based on solar position."""
        try:
            sun_state = self._hass.states.get("sun.sun")
            if not sun_state:
                return "day"
            
            elevation = float(sun_state.attributes.get("elevation", 10))
            
            if elevation > 10:
                return "day"
            elif elevation > 0:
                return "twilight"
            elif elevation > -6:
                return "civil_twilight"
            else:
                return "night"
        except Exception as e:
            _LOGGER.error("Error calculating night mode: %s", e)
            return "day"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        try:
            sun_state = self._hass.states.get("sun.sun")
            elevation = float(sun_state.attributes.get("elevation", 10)) if sun_state else 10
            azimuth = float(sun_state.attributes.get("azimuth", 0)) if sun_state else 0
            
            # Get the malus value
            native = self.native_value
            malus = NIGHT_MODE_MALUS.get(native, 0.0)
            
            return {
                "elevation": round(elevation, 2),
                "azimuth": round(azimuth, 2),
                "malus": malus
            }
        except Exception:
            return {}


class BikerSentinelPrecipitationHistory(SensorEntity):
    """24-hour precipitation history and trend sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "precip_history"
    _attr_icon = "mdi:water"
    _attr_unit_of_measurement = "mm"

    def __init__(self, hass, entry):
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_precip_history"
        self._precip_data = []  # List of (timestamp, value) tuples

    def _infer_road_state(self, precip_mm: float) -> tuple:
        """
        Infer road surface condition from precipitation and temperature.
        
        Returns: (road_state: str, traction_factor: float, malus: float)
        """
        try:
            # Get temperature
            temp_entity = self._entry.data.get(CONF_SENSOR_TEMP)
            temp = 10.0  # default safe temperature
            
            if temp_entity:
                temp_state = self._hass.states.get(temp_entity)
                if temp_state and temp_state.state not in ["unknown", "unavailable"]:
                    temp = float(temp_state.state)
            
            # Determine road state based on precipitation and temperature
            if precip_mm >= 10 and temp < 0:
                # Heavy rain + freezing = icy conditions
                return ("icy", 0.5, -8.0)
            elif precip_mm >= 10:
                # Heavy rain = sludge/standing water
                return ("sludge", 0.6, -6.0)
            elif precip_mm >= 5:
                # Moderate rain = wet roads
                return ("wet", 0.8, -3.0)
            elif precip_mm > 0:
                # Light rain = damp
                return ("damp", 0.9, -1.0)
            else:
                # No recent rain = dry
                return ("dry", 1.0, 0.0)
        
        except Exception as e:
            _LOGGER.error("Error inferring road state: %s", e)
            return ("unknown", 1.0, 0.0)

    @property
    def native_value(self):
        """Return total precipitation in 24h window."""
        try:
            rain_entity = self._entry.data.get(CONF_SENSOR_RAIN)
            if not rain_entity:
                return None
            
            rain_state = self._hass.states.get(rain_entity)
            if not rain_state or rain_state.state in ["unknown", "unavailable"]:
                return 0.0
            
            rain_value = float(rain_state.state)
            return round(rain_value, 2)
        except Exception as e:
            _LOGGER.error("Error reading precipitation history: %s", e)
            return None

    @property
    def extra_state_attributes(self):
        """Return road surface condition and traction factor."""
        try:
            precip = self.native_value or 0.0
            road_state, traction_factor, malus = self._infer_road_state(precip)
            
            return {
                "road_state": road_state,
                "traction_factor": round(traction_factor, 2),
                "road_malus": malus,
            }
        except Exception as e:
            _LOGGER.error("Error calculating road attributes: %s", e)
            return {}


class BikerSentinelTripScore(SensorEntity):
    """Trip Score - estimated safety for configured routes."""

    _attr_has_entity_name = True
    _attr_translation_key = "trip_score"
    _attr_icon = "mdi:route"
    _attr_unit_of_measurement = "/10"

    def __init__(self, hass, entry):
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_trip_score"

    @property
    def native_value(self):
        """Return estimated trip score based on configured schedules and forecast."""
        try:
            depart_time = self._entry.data.get(CONF_TRIP_DEPART_TIME)
            return_time = self._entry.data.get(CONF_TRIP_RETURN_TIME)
            weather_start = self._entry.data.get(CONF_TRIP_WEATHER_START)
            weather_end = self._entry.data.get(CONF_TRIP_WEATHER_END)
            
            if not depart_time or not return_time or not weather_start:
                return None
            
            # Calculate depart score
            depart_score = self._calculate_forecast_score(weather_start, depart_time)
            
            # Calculate return score (use same location if end location not specified)
            return_entity = weather_end or weather_start
            return_score = self._calculate_forecast_score(return_entity, return_time)
            
            # Average the two scores
            if depart_score is not None and return_score is not None:
                trip_avg = (depart_score + return_score) / 2
                return round(max(0, min(10, trip_avg)), 1)
            elif depart_score is not None:
                return depart_score
            
            return None
        except Exception as e:
            _LOGGER.error("Error calculating trip score: %s", e)
            return None

    def _calculate_forecast_score(self, weather_entity, target_time):
        """Calculate score for a specific weather entity and time."""
        try:
            if not weather_entity:
                return None
            
            w_state = self._hass.states.get(weather_entity)
            if not w_state:
                return None
            
            # Default score for current conditions
            current_condition = w_state.state
            score = self._get_score_for_condition(current_condition)
            
            return score
        except Exception:
            return None

    def _get_score_for_condition(self, condition):
        """Map weather condition to score impact."""
        condition_scores = {
            "clear": 10.0,
            "cloudy": 9.0,
            "rainy": 6.5,
            "fog": 5.0,
            "hail": 2.0,
            "snowy": 1.0,
            "lightning-rainy": 0.0,
            "partlycloudy": 9.5,
        }
        return condition_scores.get(condition, 7.5)

    @property
    def extra_state_attributes(self):
        """Return trip details."""
        return {
            "depart_time": self._entry.data.get(CONF_TRIP_DEPART_TIME),
            "return_time": self._entry.data.get(CONF_TRIP_RETURN_TIME),
            "start_location": self._entry.data.get(CONF_TRIP_WEATHER_START),
            "end_location": self._entry.data.get(CONF_TRIP_WEATHER_END),
        }


class BikerSentinelTemperatureTrend(SensorEntity):
    """Monitor temperature trends and sudden drops for icing risk."""

    _attr_has_entity_name = True
    _attr_translation_key = "temp_trend"
    _attr_icon = "mdi:thermometer-alert"

    def __init__(self, hass, entry):
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_temp_trend"
        self._temp_history = []  # List of recent temperature values

    def _get_temperature(self) -> float:
        """Get current temperature from configured sensor."""
        try:
            temp_entity = self._entry.data.get(CONF_SENSOR_TEMP)
            if not temp_entity:
                return 10.0  # Default safe temp
            
            temp_state = self._hass.states.get(temp_entity)
            if not temp_state or temp_state.state in ["unknown", "unavailable"]:
                return 10.0
            
            return float(temp_state.state)
        except Exception:
            return 10.0

    def _analyze_trend(self) -> tuple:
        """
        Analyze temperature trend.
        
        Returns: (trend: str, malus: float, risk_level: str)
        """
        try:
            current_temp = self._get_temperature()
            
            # Keep history window
            self._temp_history.append(current_temp)
            if len(self._temp_history) > TEMP_HISTORY_WINDOW:
                self._temp_history.pop(0)
            
            if len(self._temp_history) < 2:
                return ("initializing", 0.0, "normal")
            
            # Check for sudden drop
            recent_temps = self._temp_history[-3:]  # Last 3 readings
            if len(recent_temps) >= 2:
                temp_drop = recent_temps[0] - recent_temps[-1]
                
                if temp_drop > TEMP_DROP_THRESHOLD:
                    # Rapid temperature drop = icing risk
                    return ("dropping", -2.0, "warning")
                elif temp_drop < -TEMP_DROP_THRESHOLD:
                    # Rising temperature = improving conditions
                    return ("rising", 0.5, "improving")
            
            # Check if below freezing
            if current_temp < 0:
                return ("freezing", 0.0, "caution")
            
            return ("stable", 0.0, "normal")
        
        except Exception as e:
            _LOGGER.error("Error analyzing temperature trend: %s", e)
            return ("unknown", 0.0, "unknown")

    @property
    def native_value(self):
        """Return current trend status."""
        trend, _, _ = self._analyze_trend()
        return trend

    @property
    def extra_state_attributes(self):
        """Return trend analysis details."""
        trend, malus, risk = self._analyze_trend()
        current_temp = self._get_temperature()
        
        return {
            "current_temp": round(current_temp, 1),
            "malus": malus,
            "risk_level": risk,
            "history_length": len(self._temp_history),
        }


class BikerSentinelHumidityTrend(SensorEntity):
    """Monitor humidity levels for visibility impact."""

    _attr_has_entity_name = True
    _attr_translation_key = "humidity_trend"
    _attr_icon = "mdi:water-percent"
    _attr_unit_of_measurement = "%"

    def __init__(self, hass, entry):
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_humidity_trend"

    def _get_humidity(self) -> float:
        """Get humidity from weather entity or sensor."""
        try:
            # Try to get humidity from weather entity
            weather_entity = self._entry.data.get(CONF_WEATHER_ENTITY)
            if weather_entity:
                weather_state = self._hass.states.get(weather_entity)
                if weather_state:
                    humidity = weather_state.attributes.get("humidity")
                    if humidity:
                        return float(humidity)
            
            # Default if not available
            return 50.0
        except Exception:
            return 50.0

    def _infer_visibility_impact(self, humidity: float) -> tuple:
        """
        Infer visibility impact from humidity.
        
        Returns: (visibility_status: str, malus: float)
        """
        if humidity >= 70:
            return ("high", -1.5)  # Fog/mist risk
        elif humidity >= 30:
            return ("moderate", 0.0)  # Normal conditions
        else:
            return ("low", 0.0)  # Good visibility

    @property
    def native_value(self):
        """Return current humidity value."""
        return round(self._get_humidity(), 1)

    @property
    def extra_state_attributes(self):
        """Return humidity analysis."""
        humidity = self._get_humidity()
        visibility, malus = self._infer_visibility_impact(humidity)
        
        return {
            "visibility": visibility,
            "visibility_malus": malus,
        }