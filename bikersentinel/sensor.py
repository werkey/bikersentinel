"""Sensor platform for BikerSentinel - Refactored v2.0 UX."""
from __future__ import annotations

import logging
import math
from datetime import datetime, time

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
    ROAD_STATE_THRESHOLDS,
    ROAD_STATE_MALUS,
    TEMP_HISTORY_WINDOW,
    TEMP_DROP_THRESHOLD,
    TEMP_TREND_MALUS,
    HUMIDITY_THRESHOLDS,
    HUMIDITY_MALUS,
    SOLAR_BLINDNESS_THRESHOLD,
    SOLAR_BLINDNESS_MALUS,
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
    CONF_TRIP_HOME_WEATHER,
    CONF_TRIP_OFFICE_WEATHER,
    CONF_TRIP_DEPART_TIME,
    CONF_TRIP_RETURN_TIME,
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
    """Set up the BikerSentinel sensors (v2.0 - Essential Only)."""
    
    # Retrieve config data with fallbacks
    height = entry.data.get(CONF_HEIGHT) or DEFAULT_HEIGHT_CM
    weight = entry.data.get(CONF_WEIGHT) or DEFAULT_WEIGHT_KG
    bike_type = entry.data.get(CONF_BIKE_TYPE, DEFAULT_BIKE_TYPE)
    equipment = entry.data.get(CONF_EQUIPMENT, DEFAULT_EQUIPMENT)
    sensitivity = entry.data.get(CONF_SENSITIVITY, DEFAULT_SENSITIVITY)
    riding_context = entry.data.get(CONF_RIDING_CONTEXT, DEFAULT_RIDING_CONTEXT)
    trip_enabled = entry.data.get(CONF_TRIP_ENABLED, False)

    # Create the Score entity - this is the core of all calculations
    score_entity = BikerSentinelScore(
        hass, entry, height, weight, bike_type, equipment, sensitivity, riding_context
    )
    
    # Store reference for Status and Reasoning sensors
    entry.runtime_data = {"score_entity": score_entity}

    # Essential entities only
    entities = [
        score_entity,
        BikerSentinelStatus(hass, entry),
        BikerSentinelReasoning(hass, entry),
    ]
    
    # Only add trip scores if enabled
    if trip_enabled:
        entities.append(BikerSentinelTripScoreGo(hass, entry))
        entities.append(BikerSentinelTripScoreReturn(hass, entry))
        entities.append(BikerSentinelTripReasoningGo(hass, entry))
        entities.append(BikerSentinelTripScoreReturn(hass, entry))
        entities.append(BikerSentinelTripStatusReturn(hass, entry))
        entities.append(BikerSentinelTripReasoningReturn(hass, entry))

    async_add_entities(entities, True)


class BikerSentinelScore(SensorEntity):
    """Main BikerSentinel Score (0-10) - Enhanced with all internal calculations."""

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
        
        # Initialize tracking for trends
        self._attr_extra_state_attributes = {
            "reasons": [],
            "night_mode": "day",
            "road_state": "unknown",
            "temperature_trend": "stable",
            "humidity": "moderate",
            "solar_glare": "safe",
        }
        
        # Entity IDs for sensors
        self._ent_temp = entry.data.get(CONF_SENSOR_TEMP)
        self._ent_wind = entry.data.get(CONF_SENSOR_WIND)
        self._ent_rain = entry.data.get(CONF_SENSOR_RAIN)
        self._ent_weather = entry.data.get(CONF_WEATHER_ENTITY)
        self._riding_context = riding_context
        
        # Load rider-specific coefficients
        self._coef = PROTECTION_COEFS.get(bike_type, 1.2)
        self._equip_coef = EQUIPMENT_COEFS.get(equipment, 1.0)
        
        # Calculate surface area using DuBois formula
        self._surface = 0.007184 * math.pow(height, 0.725) * math.pow(weight, 0.425)
        
        # Sensitivity factor (1=Viking, 3=Normal, 5=Sensitive)
        self._sens_factor = 1.0 + ((sensitivity - 3) * 0.1)
        
        # History tracking for trends
        self._temp_history = []
        self._precip_history = {}  # Timestamp -> rainfall

    @property
    def native_value(self):
        """Calculate the complete BikerSentinel score with all advanced features."""
        reasons = []
        
        try:
            # Get current sensor states
            s_temp = self._hass.states.get(self._ent_temp)
            s_wind = self._hass.states.get(self._ent_wind)
            s_rain = self._hass.states.get(self._ent_rain)
            
            # Validate data availability
            if not s_temp or not s_wind or not s_rain:
                return None
            if s_temp.state in ["unknown", "unavailable"] or s_wind.state in ["unknown", "unavailable"]:
                return None

            t = float(s_temp.state)
            v = float(s_wind.state)
            p = float(s_rain.state) if s_rain.state not in ["unknown", "unavailable"] else 0.0
            
            # Get weather state
            weather_state = "clear"
            if self._ent_weather:
                w_state = self._hass.states.get(self._ent_weather)
                if w_state and w_state.state not in ["unknown", "unavailable"]:
                    weather_state = w_state.state

            # --- ALGORITHM STARTS ---
            score = 10.0

            # 1. SAFETY VETOES (Immediate 0.0)
            if weather_state in ["snowy", "snowy-rainy", "hail", "lightning-rainy"]:
                self._attr_extra_state_attributes["reasons"] = ["Dangerous Weather"]
                return 0.0
            if t < 1:
                self._attr_extra_state_attributes["reasons"] = ["Ice Risk"]
                return 0.0
            if v > 85:
                self._attr_extra_state_attributes["reasons"] = ["Storm Winds"]
                return 0.0

            # 2. FOG & VISIBILITY
            if weather_state == "fog":
                score -= 3.0
                reasons.append("Fog (-3)")

            # 3. NIGHT MODE WITH SOLAR ELEVATION & AZIMUTH
            try:
                sun_state = self._hass.states.get("sun.sun")
                if sun_state:
                    elevation = float(sun_state.attributes.get("elevation", 10))
                    azimuth = float(sun_state.attributes.get("azimuth", 180))
                    
                    # Determine night mode status
                    if elevation > 10:
                        night_status = "day"
                        night_malus = 0.0
                    elif elevation > 0:
                        night_status = "twilight"
                        night_malus = NIGHT_MODE_MALUS.get("twilight", -1.5)
                    elif elevation > -6:
                        night_status = "civil_twilight"
                        night_malus = NIGHT_MODE_MALUS.get("civil_twilight", -3.0)
                    else:
                        night_status = "night"
                        night_malus = NIGHT_MODE_MALUS.get("night", -5.0)
                    
                    self._attr_extra_state_attributes["night_mode"] = night_status
                    
                    if night_malus < 0:
                        score += night_malus
                        reasons.append(f"Night ({night_malus:.1f})")
                    
                    # SOLAR BLINDNESS - Glare detection
                    # Front azimuth is 90-270° (Sun ahead causes glare)
                    diff = abs(azimuth - 180)
                    if diff > 180:
                        diff = 360 - diff
                    
                    if diff < SOLAR_BLINDNESS_THRESHOLD and elevation > 5:
                        if diff < 30:
                            glare_status = "warning"
                            solar_malus = SOLAR_BLINDNESS_MALUS["warning"]
                        else:
                            glare_status = "caution"
                            solar_malus = SOLAR_BLINDNESS_MALUS["caution"]
                        
                        self._attr_extra_state_attributes["solar_glare"] = glare_status
                        score += solar_malus
                        reasons.append(f"Sun Glare ({solar_malus:.1f})")
                    else:
                        self._attr_extra_state_attributes["solar_glare"] = "safe"
                        
            except Exception as e:
                _LOGGER.debug("Could not calculate sun position: %s", e)

            # 4. WINDCHILL (Thermal Comfort - Core Algorithm)
            riding_speed = RIDING_CONTEXTS.get(self._riding_context, 80)
            total_wind = v + (riding_speed * 0.1)
            t_felt = t - (total_wind * 0.2 * self._coef)
            
            if t_felt < 15:
                raw_malus = (15 - t_felt) * 0.2 * self._surface
                final_malus = raw_malus * self._equip_coef * self._sens_factor
                score -= final_malus
                reasons.append(f"Felt Temp {t_felt:.1f}C (-{final_malus:.1f})")

            # 5. WIND STABILITY (Lateral Forces)
            if v > 35:
                malus_wind = (v - 35) * 0.15 * self._coef
                score -= malus_wind
                reasons.append(f"Wind {v}km/h (-{malus_wind:.1f})")

            # 6. RAIN (Immediate Road Hazard)
            if p > 0:
                score -= 3.0
                reasons.append(f"Rain {p}mm (-3)")

            # 7. PRECIPITATION HISTORY & ROAD STATE (24h correlation)
            # Track precipitation to infer road surface conditions
            try:
                now = datetime.now()
                self._precip_history[now] = p
                
                # Clean old history (24h window)
                cutoff = datetime.fromtimestamp(now.timestamp() - PRECIP_HISTORY_WINDOW * 3600)
                self._precip_history = {k: v for k, v in self._precip_history.items() if k > cutoff}
                
                # Calculate total rainfall in window
                total_rainfall = sum(self._precip_history.values())
                
                # Determine road state based on rainfall and temperature
                road_state = "unknown"
                road_malus = 0.0
                
                if total_rainfall == 0:
                    road_state = "dry"
                elif total_rainfall <= 5:
                    road_state = "damp"
                    road_malus = ROAD_STATE_MALUS.get("damp", -1.0)
                elif total_rainfall <= 10:
                    road_state = "wet"
                    road_malus = ROAD_STATE_MALUS.get("wet", -3.0)
                else:
                    # Check for icy conditions
                    if t < 0:
                        road_state = "icy"
                        road_malus = ROAD_STATE_MALUS.get("icy", -8.0)
                    else:
                        road_state = "sludge"
                        road_malus = ROAD_STATE_MALUS.get("sludge", -6.0)
                
                self._attr_extra_state_attributes["road_state"] = road_state
                
                if road_malus < 0:
                    score += road_malus
                    reasons.append(f"Road {road_state.capitalize()} ({road_malus:.1f})")
                    
            except Exception as e:
                _LOGGER.debug("Could not calculate road state: %s", e)

            # 8. TEMPERATURE TREND (Icing Risk)
            try:
                self._temp_history.append((datetime.now(), t))
                
                # Keep only last 6 readings
                cutoff_time = datetime.fromtimestamp(datetime.now().timestamp() - TEMP_HISTORY_WINDOW * 600)
                self._temp_history = [(ts, temp) for ts, temp in self._temp_history if ts > cutoff_time]
                
                if len(self._temp_history) >= 2:
                    oldest_temp = self._temp_history[0][1]
                    temp_diff = t - oldest_temp
                    
                    if temp_diff < -TEMP_DROP_THRESHOLD:
                        trend = "dropping"
                        trend_malus = TEMP_TREND_MALUS.get("dropping", -2.0)
                        score += trend_malus
                        reasons.append(f"Temp Dropping ({trend_malus:.1f})")
                    elif temp_diff > 3:
                        trend = "rising"
                    else:
                        trend = "stable"
                    
                    self._attr_extra_state_attributes["temperature_trend"] = trend
                    
            except Exception as e:
                _LOGGER.debug("Could not calculate temperature trend: %s", e)

            # 9. HUMIDITY & VISIBILITY
            try:
                if self._ent_weather:
                    w_state = self._hass.states.get(self._ent_weather)
                    if w_state:
                        humidity = w_state.attributes.get("humidity")
                        if humidity:
                            humidity = float(humidity)
                            
                            if humidity > 70:
                                humidity_status = "high"
                                humidity_malus = HUMIDITY_MALUS.get("high", -1.5)
                                score += humidity_malus
                                reasons.append(f"High Humidity ({humidity_malus:.1f})")
                            elif humidity > 30:
                                humidity_status = "moderate"
                            else:
                                humidity_status = "low"
                            
                            self._attr_extra_state_attributes["humidity"] = humidity_status
                            
            except Exception as e:
                _LOGGER.debug("Could not get humidity data: %s", e)

            # Final score calculation
            final_score = round(max(0, min(10, score)), 1)
            
            # Update reasons for Reasoning sensor
            self._attr_extra_state_attributes["reasons"] = reasons if reasons else ["Perfect Conditions"]
            
            return final_score
            
        except Exception as e:
            _LOGGER.error("Error calculating BikerSentinel score: %s", e)
            return None


class BikerSentinelStatus(SensorEntity):
    """Status categorization derived from score."""

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
        """Return status based on score."""
        try:
            score_entity = self._entry.runtime_data.get("score_entity")
            if not score_entity:
                return "analyzing"
            
            score = score_entity.native_value
            
            if score is None:
                return "analyzing"
            
            if score == 0:
                return "dangerous"
            elif score <= 2:
                return "critical"
            elif score <= 4:
                return "degraded"
            elif score <= 6:
                return "favorable"
            else:
                return "optimal"
                
        except Exception as e:
            _LOGGER.error("Error calculating status: %s", e)
            return "error"


class BikerSentinelReasoning(SensorEntity):
    """Detailed reasoning for the score (shows contributing factors)."""

    _attr_has_entity_name = True
    _attr_translation_key = "reasoning"
    _attr_icon = "mdi:information"

    def __init__(self, hass, entry):
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_reasoning"

    @property
    def native_value(self):
        """Return the main reason affecting the score."""
        try:
            score_entity = self._entry.runtime_data.get("score_entity")
            if not score_entity:
                return "Initializing..."
            
            reasons = score_entity.extra_state_attributes.get("reasons", [])
            
            if not reasons:
                return "Perfect Conditions"
            
            # Return the primary reason
            return reasons[0]
            
        except Exception:
            return "Calculating..."

    @property
    def extra_state_attributes(self):
        """Return all reasons as attributes."""
        try:
            score_entity = self._entry.runtime_data.get("score_entity")
            if not score_entity:
                return {}
            
            return {
                "reasons": score_entity.extra_state_attributes.get("reasons", []),
                "night_mode": score_entity.extra_state_attributes.get("night_mode", "day"),
                "road_state": score_entity.extra_state_attributes.get("road_state", "unknown"),
                "temperature_trend": score_entity.extra_state_attributes.get("temperature_trend", "stable"),
                "humidity": score_entity.extra_state_attributes.get("humidity", "moderate"),
                "solar_glare": score_entity.extra_state_attributes.get("solar_glare", "safe"),
            }
        except Exception:
            return {}


class BikerSentinelTripScoreGo(SensorEntity):
    """Trip Score for outbound journey (departure time)."""

    _attr_has_entity_name = True
    _attr_translation_key = "trip_score_go"
    _attr_native_unit_of_measurement = "/10"
    _attr_icon = "mdi:bike"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, entry):
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_trip_score_go"

    @property
    def native_value(self):
        """Calculate score for outbound trip (home → office on full route)."""
        try:
            # Get trip configuration
            home_weather_entity = self._entry.data.get(CONF_TRIP_HOME_WEATHER)
            office_weather_entity = self._entry.data.get(CONF_TRIP_OFFICE_WEATHER)
            depart_time_str = self._entry.data.get(CONF_TRIP_DEPART_TIME)
            
            if not home_weather_entity or not office_weather_entity or not depart_time_str:
                return None
            
            # Get weather at both locations
            home_weather = self._hass.states.get(home_weather_entity)
            office_weather = self._hass.states.get(office_weather_entity)
            
            if not home_weather or not office_weather:
                return None
            
            reasons = []
            score = 8.0  # Base trip score
            
            # Analyze HOME weather (starting point)
            home_reasons = self._analyze_weather(home_weather, "Home")
            score += home_reasons["malus"]
            reasons.extend(home_reasons["reasons"])
            
            # Analyze OFFICE weather (destination)
            office_reasons = self._analyze_weather(office_weather, "Office")
            score += office_reasons["malus"]
            reasons.extend(office_reasons["reasons"])
            
            # Store reasons in attributes
            self._attr_extra_state_attributes = {
                "reasons": reasons if reasons else ["Good conditions"],
                "home_location": home_weather_entity,
                "office_location": office_weather_entity,
            }
            
            return round(max(0, min(10, score)), 1)
            
        except Exception as e:
            _LOGGER.error("Error calculating trip score (go): %s", e)
            return None
    
    def _analyze_weather(self, weather_state, location_name):
        """Analyze weather conditions and return malus + reasons."""
        reasons = []
        malus = 0.0
        
        # Safety vetoes
        if weather_state.state in ["snowy", "lightning-rainy", "hail"]:
            return {"malus": -8.0, "reasons": [f"{location_name}: Dangerous Weather"]}
        
        # Weather conditions
        if weather_state.state == "rainy":
            malus -= 1.5
            reasons.append(f"{location_name}: Rain (-1.5)")
        elif weather_state.state == "fog":
            malus -= 1.0
            reasons.append(f"{location_name}: Fog (-1.0)")
        elif weather_state.state == "cloudy":
            malus -= 0.3
            reasons.append(f"{location_name}: Cloudy (-0.3)")
        
        # Temperature
        try:
            temp = weather_state.attributes.get("temperature")
            if temp:
                temp = float(temp)
                if temp < 5:
                    malus -= 1.0
                    reasons.append(f"{location_name}: Cold {temp}°C (-1.0)")
                elif temp > 30:
                    malus -= 0.3
                    reasons.append(f"{location_name}: Hot {temp}°C (-0.3)")
        except Exception:
            pass
        
        # Wind
        try:
            wind = weather_state.attributes.get("wind_speed")
            if wind:
                wind = float(wind)
                if wind > 40:
                    malus -= 0.7
                    reasons.append(f"{location_name}: Wind {wind}km/h (-0.7)")
        except Exception:
            pass
        
        # Humidity
        try:
            humidity = weather_state.attributes.get("humidity")
            if humidity:
                humidity = float(humidity)
                if humidity > 85:
                    malus -= 0.5
                    reasons.append(f"{location_name}: Humidity {humidity}% (-0.5)")
        except Exception:
            pass
        
        return {"malus": malus, "reasons": reasons}


class BikerSentinelTripScoreReturn(SensorEntity):
    """Trip Score for return journey (return time)."""

    _attr_has_entity_name = True
    _attr_translation_key = "trip_score_return"
    _attr_native_unit_of_measurement = "/10"
    _attr_icon = "mdi:bike-fast"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, entry):
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_trip_score_return"

    @property
    def native_value(self):
        """Calculate score for return trip (office → home on full route)."""
        try:
            # Get trip configuration
            home_weather_entity = self._entry.data.get(CONF_TRIP_HOME_WEATHER)
            office_weather_entity = self._entry.data.get(CONF_TRIP_OFFICE_WEATHER)
            return_time_str = self._entry.data.get(CONF_TRIP_RETURN_TIME)
            
            if not home_weather_entity or not office_weather_entity or not return_time_str:
                return None
            
            # Get weather at both locations
            home_weather = self._hass.states.get(home_weather_entity)
            office_weather = self._hass.states.get(office_weather_entity)
            
            if not home_weather or not office_weather:
                return None
            
            reasons = []
            score = 8.0  # Base trip score
            
            # Analyze OFFICE weather (starting point for return)
            office_reasons = self._analyze_weather(office_weather, "Office")
            score += office_reasons["malus"]
            reasons.extend(office_reasons["reasons"])
            
            # Analyze HOME weather (destination for return)
            home_reasons = self._analyze_weather(home_weather, "Home")
            score += home_reasons["malus"]
            reasons.extend(home_reasons["reasons"])
            
            # Store reasons in attributes
            self._attr_extra_state_attributes = {
                "reasons": reasons if reasons else ["Good conditions"],
                "office_location": office_weather_entity,
                "home_location": home_weather_entity,
            }
            
            return round(max(0, min(10, score)), 1)
            
        except Exception as e:
            _LOGGER.error("Error calculating trip score (return): %s", e)
            return None
    
    def _analyze_weather(self, weather_state, location_name):
        """Analyze weather conditions and return malus + reasons."""
        reasons = []
        malus = 0.0
        
        # Safety vetoes
        if weather_state.state in ["snowy", "lightning-rainy", "hail"]:
            return {"malus": -8.0, "reasons": [f"{location_name}: Dangerous Weather"]}
        
        # Weather conditions
        if weather_state.state == "rainy":
            malus -= 1.5
            reasons.append(f"{location_name}: Rain (-1.5)")
        elif weather_state.state == "fog":
            malus -= 1.0
            reasons.append(f"{location_name}: Fog (-1.0)")
        elif weather_state.state == "cloudy":
            malus -= 0.3
            reasons.append(f"{location_name}: Cloudy (-0.3)")
        
        # Temperature
        try:
            temp = weather_state.attributes.get("temperature")
            if temp:
                temp = float(temp)
                if temp < 5:
                    malus -= 1.0
                    reasons.append(f"{location_name}: Cold {temp}°C (-1.0)")
                elif temp > 30:
                    malus -= 0.3
                    reasons.append(f"{location_name}: Hot {temp}°C (-0.3)")
        except Exception:
            pass
        
        # Wind
        try:
            wind = weather_state.attributes.get("wind_speed")
            if wind:
                wind = float(wind)
                if wind > 40:
                    malus -= 0.7
                    reasons.append(f"{location_name}: Wind {wind}km/h (-0.7)")
        except Exception:
            pass
        
        # Humidity
        try:
            humidity = weather_state.attributes.get("humidity")
            if humidity:
                humidity = float(humidity)
                if humidity > 85:
                    malus -= 0.5
                    reasons.append(f"{location_name}: Humidity {humidity}% (-0.5)")
        except Exception:
            pass
        
        return {"malus": malus, "reasons": reasons}


class BikerSentinelTripStatusGo(SensorEntity):
    """Trip Status for outbound journey (derived from score)."""

    _attr_has_entity_name = True
    _attr_translation_key = "trip_status_go"
    _attr_icon = "mdi:bike"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["optimal", "favorable", "degraded", "critical", "dangerous", "analyzing", "error"]

    def __init__(self, hass, entry):
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_trip_status_go"

    @property
    def native_value(self):
        """Return status based on trip score go."""
        try:
            score_entity = None
            # Find the TripScoreGo entity in the hass state
            for entity_id in self._hass.states.entity_ids():
                if "trip_score_go" in entity_id:
                    state = self._hass.states.get(entity_id)
                    if state and state.state not in ["unknown", "unavailable"]:
                        score = float(state.state)
                        
                        if score == 0:
                            return "dangerous"
                        elif score <= 2:
                            return "critical"
                        elif score <= 4:
                            return "degraded"
                        elif score <= 6:
                            return "favorable"
                        else:
                            return "optimal"
            
            return "analyzing"
            
        except Exception as e:
            _LOGGER.error("Error calculating trip status (go): %s", e)
            return "error"


class BikerSentinelTripStatusReturn(SensorEntity):
    """Trip Status for return journey (derived from score)."""

    _attr_has_entity_name = True
    _attr_translation_key = "trip_status_return"
    _attr_icon = "mdi:bike-fast"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["optimal", "favorable", "degraded", "critical", "dangerous", "analyzing", "error"]

    def __init__(self, hass, entry):
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_trip_status_return"

    @property
    def native_value(self):
        """Return status based on trip score return."""
        try:
            # Find the TripScoreReturn entity in the hass state
            for entity_id in self._hass.states.entity_ids():
                if "trip_score_return" in entity_id:
                    state = self._hass.states.get(entity_id)
                    if state and state.state not in ["unknown", "unavailable"]:
                        score = float(state.state)
                        
                        if score == 0:
                            return "dangerous"
                        elif score <= 2:
                            return "critical"
                        elif score <= 4:
                            return "degraded"
                        elif score <= 6:
                            return "favorable"
                        else:
                            return "optimal"
            
            return "analyzing"
            
        except Exception as e:
            _LOGGER.error("Error calculating trip status (return): %s", e)
            return "error"


class BikerSentinelTripReasoningGo(SensorEntity):
    """Trip Reasoning for outbound journey (explains score factors)."""

    _attr_has_entity_name = True
    _attr_translation_key = "trip_reasoning_go"
    _attr_icon = "mdi:bike"

    def __init__(self, hass, entry):
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_trip_reasoning_go"

    @property
    def native_value(self):
        """Return the primary reason affecting the outbound trip score."""
        try:
            # Find the TripScoreGo entity to get reasons
            for entity_id in self._hass.states.entity_ids():
                if "trip_score_go" in entity_id:
                    state = self._hass.states.get(entity_id)
                    if state:
                        reasons = state.attributes.get("reasons", [])
                        if reasons:
                            return reasons[0]
                        return "Good conditions"
            
            return "Analyzing..."
            
        except Exception as e:
            _LOGGER.error("Error calculating trip reasoning (go): %s", e)
            return "Calculating..."

    @property
    def extra_state_attributes(self):
        """Return all reasons as attributes."""
        try:
            for entity_id in self._hass.states.entity_ids():
                if "trip_score_go" in entity_id:
                    state = self._hass.states.get(entity_id)
                    if state:
                        return {
                            "reasons": state.attributes.get("reasons", []),
                            "destination": state.attributes.get("destination", "unknown"),
                        }
            return {}
        except Exception:
            return {}


class BikerSentinelTripReasoningReturn(SensorEntity):
    """Trip Reasoning for return journey (explains score factors)."""

    _attr_has_entity_name = True
    _attr_translation_key = "trip_reasoning_return"
    _attr_icon = "mdi:bike-fast"

    def __init__(self, hass, entry):
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_trip_reasoning_return"

    @property
    def native_value(self):
        """Return the primary reason affecting the return trip score."""
        try:
            # Find the TripScoreReturn entity to get reasons
            for entity_id in self._hass.states.entity_ids():
                if "trip_score_return" in entity_id:
                    state = self._hass.states.get(entity_id)
                    if state:
                        reasons = state.attributes.get("reasons", [])
                        if reasons:
                            return reasons[0]
                        return "Good conditions"
            
            return "Analyzing..."
            
        except Exception as e:
            _LOGGER.error("Error calculating trip reasoning (return): %s", e)
            return "Calculating..."

    @property
    def extra_state_attributes(self):
        """Return all reasons as attributes."""
        try:
            for entity_id in self._hass.states.entity_ids():
                if "trip_score_return" in entity_id:
                    state = self._hass.states.get(entity_id)
                    if state:
                        return {
                            "reasons": state.attributes.get("reasons", []),
                            "destination": state.attributes.get("destination", "unknown"),
                        }
            return {}
        except Exception:
            return {}
