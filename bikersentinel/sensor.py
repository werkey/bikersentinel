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
    MACHINE_TYPES,
    EQUIPMENT_LEVELS,
    RIDING_CONTEXTS,
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
    CONF_RAIN_RATIO,
    CONF_FOG_RATIO,
    CONF_CLOUDY_RATIO,
    CONF_COLD_RATIO,
    CONF_HOT_RATIO,
    CONF_WIND_RATIO,
    CONF_HUMIDITY_RATIO,
    CONF_NIGHT_RATIO,
    CONF_ROAD_STATE_RATIO,
    DEFAULT_HEIGHT_CM,
    DEFAULT_WEIGHT_KG,
    DEFAULT_BIKE_TYPE,
    DEFAULT_EQUIPMENT,
    DEFAULT_SENSITIVITY,
    DEFAULT_RIDING_CONTEXT,
    DEFAULT_RAIN_RATIO,
    DEFAULT_FOG_RATIO,
    DEFAULT_CLOUDY_RATIO,
    DEFAULT_COLD_RATIO,
    DEFAULT_HOT_RATIO,
    DEFAULT_WIND_RATIO,
    DEFAULT_HUMIDITY_RATIO,
    DEFAULT_NIGHT_RATIO,
    DEFAULT_ROAD_STATE_RATIO,
)

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
    CONF_RAIN_RATIO,
    CONF_FOG_RATIO,
    CONF_CLOUDY_RATIO,
    CONF_COLD_RATIO,
    CONF_HOT_RATIO,
    CONF_WIND_RATIO,
    CONF_HUMIDITY_RATIO,
    CONF_NIGHT_RATIO,
    CONF_ROAD_STATE_RATIO,
    DEFAULT_RAIN_RATIO,
    DEFAULT_FOG_RATIO,
    DEFAULT_CLOUDY_RATIO,
    DEFAULT_COLD_RATIO,
    DEFAULT_HOT_RATIO,
    DEFAULT_WIND_RATIO,
    DEFAULT_HUMIDITY_RATIO,
    DEFAULT_NIGHT_RATIO,
    DEFAULT_ROAD_STATE_RATIO,
)

_LOGGER = logging.getLogger(__name__)


class BikerSentinelConfigService:
    """Expose a service to update malus ratios as a workaround for missing options flow UI."""
    def __init__(self, hass):
        self.hass = hass
        self._service_registered = False

    def register(self):
        if self._service_registered:
            return
        import voluptuous as vol
        self.hass.services.async_register(
            DOMAIN,
            "set_malus_ratios",
            self.async_handle_set_malus_ratios,
            schema=vol.Schema({
                vol.Required("entry_id"): str,  # Specific entry to modify
                vol.Optional("rain_ratio"): float,
                vol.Optional("fog_ratio"): float,
                vol.Optional("cloudy_ratio"): float,
                vol.Optional("cold_ratio"): float,
                vol.Optional("hot_ratio"): float,
                vol.Optional("wind_ratio"): float,
                vol.Optional("humidity_ratio"): float,
                vol.Optional("night_ratio"): float,
                vol.Optional("road_state_ratio"): float,
            })
        )
        self._service_registered = True
        _LOGGER.info("BikerSentinel config service registered")

    async def async_handle_set_malus_ratios(self, call):
        entry_id = call.data.get("entry_id")
        if not entry_id:
            _LOGGER.error("entry_id is required for set_malus_ratios service")
            return
            
        value_map = {k: v for k, v in call.data.items() if k.endswith("_ratio") and k != "entry_id"}
        
        # Find the specific config entry
        entry = None
        for e in self.hass.config_entries.async_entries(DOMAIN):
            if e.entry_id == entry_id:
                entry = e
                break
        
        if not entry:
            _LOGGER.error("BikerSentinel entry with id %s not found", entry_id)
            return
            
        # Update options
        options = dict(entry.options)
        options.update(value_map)
        self.hass.config_entries.async_update_entry(entry, options=options)
        _LOGGER.warning("[BikerSentinel] Updated malus ratios for entry %s: %s", entry_id, value_map)


def _create_device_info(entry: ConfigEntry) -> DeviceInfo | None:
    """Create device info for BikerSentinel integration."""
    try:
        from homeassistant.helpers.device_registry import DeviceInfo
        device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"BikerSentinel ({entry.data.get(CONF_BIKE_TYPE, DEFAULT_BIKE_TYPE)})",
            manufacturer="BikerSentinel",
            model="Weather-Aware Bike Safety Monitor",
            sw_version="2.0.0",
        )
        _LOGGER.debug("Created device info for BikerSentinel: %s", device_info.get('name', 'Unknown'))
        return device_info
    except ImportError:
        # For testing environments without Home Assistant
        _LOGGER.debug("DeviceInfo import failed, returning None")
        return None


def _get_ratio_value(entry: ConfigEntry, ratio_key: str, default_value: float) -> float:
    """Get ratio value from options first, then data, then default."""
    # Check options first (user-configurable)
    if hasattr(entry, 'options') and entry.options and ratio_key in entry.options:
        return entry.options[ratio_key]
    # Then check data (from initial config)
    if ratio_key in entry.data:
        return entry.data[ratio_key]
    # Finally use default
    return default_value


def analyze_weather_conditions(weather_state, location_name, rain_ratio=1.0, fog_ratio=1.0, cloudy_ratio=1.0, 
                               cold_ratio=1.0, hot_ratio=1.0, wind_ratio=1.0, humidity_ratio=1.0):
    """Analyze weather conditions and return malus + reasons."""
    reasons = []
    malus = 0.0
    
    # Safety vetoes
    if weather_state.state in ["snowy", "lightning-rainy", "hail"]:
        return {"malus": -8.0, "reasons": [f"{location_name}: Dangerous Weather"]}
    
    # Weather conditions
    if weather_state.state == "rainy":
        malus -= 1.5 * rain_ratio
        reasons.append(f"{location_name}: Rain ({-1.5 * rain_ratio:.1f})")
    elif weather_state.state == "fog":
        malus -= 1.0 * fog_ratio
        reasons.append(f"{location_name}: Fog ({-1.0 * fog_ratio:.1f})")
    elif weather_state.state == "cloudy":
        malus -= 0.3 * cloudy_ratio
        reasons.append(f"{location_name}: Cloudy ({-0.3 * cloudy_ratio:.1f})")
    
    # Temperature
    try:
        temp = weather_state.attributes.get("temperature")
        if temp:
            temp = float(temp)
            if temp < 5:
                malus -= 1.0 * cold_ratio
                reasons.append(f"{location_name}: Cold {temp}°C ({-1.0 * cold_ratio:.1f})")
            elif temp > 30:
                malus -= 0.3 * hot_ratio
                reasons.append(f"{location_name}: Hot {temp}°C ({-0.3 * hot_ratio:.1f})")
    except Exception:
        pass
    
    # Wind
    try:
        wind = weather_state.attributes.get("wind_speed")
        if wind:
            wind = float(wind)
            if wind > 40:
                malus -= 0.7 * wind_ratio
                reasons.append(f"{location_name}: Wind {wind}km/h ({-0.7 * wind_ratio:.1f})")
    except Exception:
        pass
    
    # Humidity
    try:
        humidity = weather_state.attributes.get("humidity")
        if humidity:
            humidity = float(humidity)
            if humidity > 85:
                malus -= 0.5 * humidity_ratio
                reasons.append(f"{location_name}: Humidity {humidity}% ({-0.5 * humidity_ratio:.1f})")
    except Exception:
        pass
    
    return {"malus": malus, "reasons": reasons}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BikerSentinel sensors (v2.0 - Essential Only)."""
    _LOGGER.info("Setting up BikerSentinel sensors for entry: %s", entry.entry_id)
    _LOGGER.info("Setting up BikerSentinel sensors for entry: %s", entry.entry_id)
    
    # Retrieve config data with fallbacks
    height = entry.data.get(CONF_HEIGHT) or DEFAULT_HEIGHT_CM
    weight = entry.data.get(CONF_WEIGHT) or DEFAULT_WEIGHT_KG
    bike_type = entry.data.get(CONF_BIKE_TYPE, DEFAULT_BIKE_TYPE)
    equipment = entry.data.get(CONF_EQUIPMENT, DEFAULT_EQUIPMENT)
    sensitivity = entry.data.get(CONF_SENSITIVITY, DEFAULT_SENSITIVITY)
    riding_context = entry.data.get(CONF_RIDING_CONTEXT, DEFAULT_RIDING_CONTEXT)
    trip_enabled = entry.data.get(CONF_TRIP_ENABLED, False)
    
    # Malus ratios (check options first, then data)
    rain_ratio = _get_ratio_value(entry, CONF_RAIN_RATIO, DEFAULT_RAIN_RATIO)
    fog_ratio = _get_ratio_value(entry, CONF_FOG_RATIO, DEFAULT_FOG_RATIO)
    cloudy_ratio = _get_ratio_value(entry, CONF_CLOUDY_RATIO, DEFAULT_CLOUDY_RATIO)
    cold_ratio = _get_ratio_value(entry, CONF_COLD_RATIO, DEFAULT_COLD_RATIO)
    hot_ratio = _get_ratio_value(entry, CONF_HOT_RATIO, DEFAULT_HOT_RATIO)
    wind_ratio = _get_ratio_value(entry, CONF_WIND_RATIO, DEFAULT_WIND_RATIO)
    humidity_ratio = _get_ratio_value(entry, CONF_HUMIDITY_RATIO, DEFAULT_HUMIDITY_RATIO)
    night_ratio = _get_ratio_value(entry, CONF_NIGHT_RATIO, DEFAULT_NIGHT_RATIO)
    road_state_ratio = _get_ratio_value(entry, CONF_ROAD_STATE_RATIO, DEFAULT_ROAD_STATE_RATIO)

    # Create the Score entity - this is the core of all calculations
    score_entity = BikerSentinelScore(
        hass, entry, height, weight, bike_type, equipment, sensitivity, riding_context,
        rain_ratio, fog_ratio, cloudy_ratio, cold_ratio, hot_ratio, wind_ratio, humidity_ratio, night_ratio, road_state_ratio
    )
    
    # Create trip score entities if enabled (needed for status/reasoning references)
    trip_score_go = None
    trip_score_return = None
    if trip_enabled:
        trip_score_go = BikerSentinelTripScoreGo(hass, entry)
        trip_score_return = BikerSentinelTripScoreReturn(hass, entry)
    
    # Store references for Status and Reasoning sensors
    entry.runtime_data = {
        "score_entity": score_entity,
        "trip_score_go": trip_score_go,
        "trip_score_return": trip_score_return,
    }

    # Essential entities: Score, Status, Reasoning
    entities = [
        score_entity,
        BikerSentinelStatus(hass, entry),
        BikerSentinelReasoning(hass, entry),
    ]
    
    # Only add trip entities if enabled (9 total: 3 instant + 3 outbound + 3 return)
    if trip_enabled:
        entities.append(trip_score_go)
        entities.append(BikerSentinelTripStatusGo(hass, entry))
        entities.append(BikerSentinelTripReasoningGo(hass, entry))
        entities.append(trip_score_return)
        entities.append(BikerSentinelTripStatusReturn(hass, entry))
        entities.append(BikerSentinelTripReasoningReturn(hass, entry))

    _LOGGER.info("Adding %d BikerSentinel entities", len(entities))
    async_add_entities(entities, True)
    
    # Log device info for debugging
    for entity in entities[:1]:  # Log only first entity to avoid spam
        if entity._attr_device_info:
            _LOGGER.info("Entity %s has device_info: %s", entity._attr_unique_id, entity._attr_device_info)
        else:
            _LOGGER.warning("Entity %s has no device_info", entity._attr_unique_id)


class BikerSentinelScore(SensorEntity):
    """Main BikerSentinel Score (0-10) - Enhanced with all internal calculations."""

    _attr_has_entity_name = True
    _attr_translation_key = "score"
    _attr_native_unit_of_measurement = "/10"
    _attr_icon = "mdi:motorbike"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, entry, height, weight, bike_type, equipment, sensitivity, riding_context,
                 rain_ratio, fog_ratio, cloudy_ratio, cold_ratio, hot_ratio, wind_ratio, humidity_ratio, night_ratio, road_state_ratio):
        """Initialize the score sensor."""
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_score"
        self._attr_device_info = _create_device_info(entry)
        self._attr_extra_state_attributes = {}  # Initialize attribute storage
        
        # User profile parameters
        self._attr_unique_id = f"{entry.entry_id}_score"
        
        # Malus ratios
        self._rain_ratio = rain_ratio
        self._fog_ratio = fog_ratio
        self._cloudy_ratio = cloudy_ratio
        self._cold_ratio = cold_ratio
        self._hot_ratio = hot_ratio
        self._wind_ratio = wind_ratio
        self._humidity_ratio = humidity_ratio
        self._night_ratio = night_ratio
        self._road_state_ratio = road_state_ratio
        
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
                fog_malus = -3.0 * self._fog_ratio
                score += fog_malus
                reasons.append(f"Fog ({fog_malus:.2f})")

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
                        adjusted_night_malus = night_malus * self._night_ratio
                        score += adjusted_night_malus
                        reasons.append(f"Night ({adjusted_night_malus:.2f})")
                    
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
                        adjusted_solar_malus = solar_malus * self._night_ratio
                        score += adjusted_solar_malus
                        reasons.append(f"Sun Glare ({adjusted_solar_malus:.2f})")
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
                adjusted_malus = final_malus * self._cold_ratio
                score -= adjusted_malus
            # 5. WIND STABILITY (Lateral Forces)
            if v > 35:
                malus_wind = (v - 35) * 0.15 * self._coef
                adjusted_wind_malus = malus_wind * self._wind_ratio
                score -= adjusted_wind_malus
                reasons.append(f"Wind {v}km/h (-{adjusted_wind_malus:.2f})")

            # 6. RAIN (Immediate Road Hazard)
            if p > 0:
                rain_malus = -3.0 * self._rain_ratio
                score += rain_malus
                reasons.append(f"Rain {p}mm ({rain_malus:.2f})")
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
                
                self._attr_extra_state_attributes["road_state"] = road_state
                
                if road_malus < 0:
                    adjusted_road_malus = road_malus * self._road_state_ratio
                    score += adjusted_road_malus
                    reasons.append(f"Road {road_state.capitalize()} ({adjusted_road_malus:.2f})")
                    
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
                    if temp_diff < -TEMP_DROP_THRESHOLD:
                        trend = "dropping"
                        trend_malus = TEMP_TREND_MALUS.get("dropping", -2.0)
                        adjusted_trend_malus = trend_malus * self._cold_ratio
                        score += adjusted_trend_malus
                        reasons.append(f"Temp Dropping ({adjusted_trend_malus:.2f})")
                    elif temp_diff > 3:
                        reasons.append(f"Temp Dropping ({trend_malus:.2f})")
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
                            if humidity > 70:
                                humidity_status = "high"
                                humidity_malus = HUMIDITY_MALUS.get("high", -1.5)
                                adjusted_humidity_malus = humidity_malus * self._humidity_ratio
                                score += adjusted_humidity_malus
                                reasons.append(f"High Humidity ({adjusted_humidity_malus:.2f})")
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
    
    @property
    def extra_state_attributes(self):
        """Return extra state attributes with all score factors."""
        return self._attr_extra_state_attributes


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
        self._attr_device_info = _create_device_info(entry)

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
        self._attr_device_info = _create_device_info(entry)

    @property
    def native_value(self):
        """Return all reasons affecting the score with total malus."""
        try:
            score_entity = self._entry.runtime_data.get("score_entity")
            if not score_entity:
                return "Initializing..."
            
            reasons = score_entity.extra_state_attributes.get("reasons", [])
            score = score_entity.native_value
            
            if not reasons or score is None:
                return "Perfect Conditions"
            
            # Calculate total malus that explains the score
            total_malus = 10.0 - score
            
            # Show all factors exhaustively
            return f"{' + '.join(reasons)} = Total malus -{total_malus:.1f}"
            
        except Exception:
            return "Calculating..."

    @property
    def extra_state_attributes(self):
        """Return detailed breakdown of all factors affecting the score."""
        try:
            score_entity = self._entry.runtime_data.get("score_entity")
            if not score_entity:
                return {}
            
            score = score_entity.native_value
            total_malus = (10.0 - score) if score is not None else 0.0
            
            return {
                "all_factors": score_entity.extra_state_attributes.get("reasons", []),
                "total_malus": round(total_malus, 1),
                "score_final": score,
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
        self._attr_device_info = _create_device_info(entry)
        self._attr_extra_state_attributes = {}  # Initialize attribute storage

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
            
            # Safety vetoes for trip (same as instant score)
            if home_weather.state in ["snowy", "snowy-rainy", "hail", "lightning-rainy"] or \
               office_weather.state in ["snowy", "snowy-rainy", "hail", "lightning-rainy"]:
                self._attr_extra_state_attributes = {
                    "reasons": ["Dangerous Weather"],
                    "home_location": home_weather_entity,
                    "office_location": office_weather_entity,
                }
                return 0.0
            
            reasons = []
            score = 10.0  # Base score for trip forecasts
            
            # Analyze HOME weather (starting point)
            rain_ratio = _get_ratio_value(self._entry, CONF_RAIN_RATIO, DEFAULT_RAIN_RATIO)
            fog_ratio = _get_ratio_value(self._entry, CONF_FOG_RATIO, DEFAULT_FOG_RATIO)
            cloudy_ratio = _get_ratio_value(self._entry, CONF_CLOUDY_RATIO, DEFAULT_CLOUDY_RATIO)
            cold_ratio = _get_ratio_value(self._entry, CONF_COLD_RATIO, DEFAULT_COLD_RATIO)
            hot_ratio = _get_ratio_value(self._entry, CONF_HOT_RATIO, DEFAULT_HOT_RATIO)
            wind_ratio = _get_ratio_value(self._entry, CONF_WIND_RATIO, DEFAULT_WIND_RATIO)
            humidity_ratio = _get_ratio_value(self._entry, CONF_HUMIDITY_RATIO, DEFAULT_HUMIDITY_RATIO)
            home_reasons = analyze_weather_conditions(home_weather, "Home", rain_ratio, fog_ratio, cloudy_ratio, cold_ratio, hot_ratio, wind_ratio, humidity_ratio)
            
            # Analyze OFFICE weather (destination)
            office_reasons = analyze_weather_conditions(office_weather, "Office", rain_ratio, fog_ratio, cloudy_ratio, cold_ratio, hot_ratio, wind_ratio, humidity_ratio)
            
            # Average the weather malus for the trip
            avg_weather_malus = (home_reasons["malus"] + office_reasons["malus"]) / 2
            score += avg_weather_malus
            
            # Create clear weather justification showing the average calculation
            home_malus = home_reasons["malus"]
            office_malus = office_reasons["malus"]
            if home_malus != 0 or office_malus != 0:
                weather_details = []
                if home_malus != 0:
                    weather_details.append(f"Home {home_malus:+.2f}")
                if office_malus != 0:
                    weather_details.append(f"Office {office_malus:+.2f}")
                if weather_details:
                    reasons.append(f"Weather average: {' + '.join(weather_details)} = {avg_weather_malus:+.2f}")
            
            # Add individual weather details for transparency
            reasons.extend(home_reasons["reasons"])
            reasons.extend(office_reasons["reasons"])
            
            # Add road state malus if forecast indicates rain
            has_road_state = False  # Trip forecasts don't have road state sensors
            if home_weather.state == "rainy" or office_weather.state == "rainy":
                score += -0.5
            if not has_road_state and (home_weather.state == "rainy" or office_weather.state == "rainy"):
                score += -0.5
                reasons.append("Road state: Wet (-0.5)")
            
            # Add road state malus from previous day (if any)
            instant_reasons = self._entry.runtime_data["score_entity"].extra_state_attributes.get("reasons", [])
            for reason in instant_reasons:
                if "Road state:" in reason:
                    if "(-0.5)" in reason:
                        score += -0.5
                        reasons.append(f"Previous day: {reason}")
                    elif "(-1.0)" in reason:
                        score += -1.0
                        reasons.append(f"Previous day: {reason}")
            
            # Check for night mode at departure time
            sun_state = self._hass.states.get("sun.sun")
            if sun_state:
                next_rising = sun_state.attributes.get("next_rising")
                next_setting = sun_state.attributes.get("next_setting")
                if next_rising and next_setting:
                    try:
                        rising_time = datetime.fromisoformat(next_rising).time()
                        setting_time = datetime.fromisoformat(next_setting).time()
                        depart_time = datetime.strptime(depart_time_str, "%H:%M").time()
                        if setting_time <= depart_time or depart_time <= rising_time:
                            score += NIGHT_MODE_MALUS
                            reasons.append(f"Trip at night ({NIGHT_MODE_MALUS})")
                    except (ValueError, TypeError):
                        _LOGGER.warning("Failed to parse sun times for trip night check")
            
            # Store reasons in attributes
            final_score = round(max(0, min(10, score)), 1)
            
            self._attr_extra_state_attributes = {
                "reasons": reasons if reasons else ["Good conditions"],
                "home_location": home_weather_entity,
                "office_location": office_weather_entity,
            }
            
            return final_score
            
        except Exception as e:
            _LOGGER.error("Error calculating trip score (go): %s", e)
            return None
    
    @property
    def extra_state_attributes(self):
        """Return extra state attributes with trip details."""
        return self._attr_extra_state_attributes


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
        self._attr_device_info = _create_device_info(entry)
        self._attr_extra_state_attributes = {}  # Initialize attribute storage

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
            score = 10.0  # Base score for trip forecasts
            
            # Analyze OFFICE weather (starting point for return)
            rain_ratio = _get_ratio_value(self._entry, CONF_RAIN_RATIO, DEFAULT_RAIN_RATIO)
            fog_ratio = _get_ratio_value(self._entry, CONF_FOG_RATIO, DEFAULT_FOG_RATIO)
            cloudy_ratio = _get_ratio_value(self._entry, CONF_CLOUDY_RATIO, DEFAULT_CLOUDY_RATIO)
            cold_ratio = _get_ratio_value(self._entry, CONF_COLD_RATIO, DEFAULT_COLD_RATIO)
            hot_ratio = _get_ratio_value(self._entry, CONF_HOT_RATIO, DEFAULT_HOT_RATIO)
            wind_ratio = _get_ratio_value(self._entry, CONF_WIND_RATIO, DEFAULT_WIND_RATIO)
            humidity_ratio = _get_ratio_value(self._entry, CONF_HUMIDITY_RATIO, DEFAULT_HUMIDITY_RATIO)
            office_reasons = analyze_weather_conditions(office_weather, "Office", rain_ratio, fog_ratio, cloudy_ratio, cold_ratio, hot_ratio, wind_ratio, humidity_ratio)
            
            # Analyze HOME weather (destination for return)
            home_reasons = analyze_weather_conditions(home_weather, "Home", rain_ratio, fog_ratio, cloudy_ratio, cold_ratio, hot_ratio, wind_ratio, humidity_ratio)
            
            # Average the weather malus for the trip
            avg_weather_malus = (home_reasons["malus"] + office_reasons["malus"]) / 2
            score += avg_weather_malus
            
            # Create clear weather justification showing the average calculation
            home_malus = home_reasons["malus"]
            office_malus = office_reasons["malus"]
            if home_malus != 0 or office_malus != 0:
                weather_details = []
                if home_malus != 0:
                    weather_details.append(f"Home {home_malus:+.2f}")
                if office_malus != 0:
                    weather_details.append(f"Office {office_malus:+.2f}")
                if weather_details:
                    reasons.append(f"Weather average: {' + '.join(weather_details)} = {avg_weather_malus:+.2f}")
            
            # Add individual weather details for transparency
            reasons.extend(office_reasons["reasons"])
            reasons.extend(home_reasons["reasons"])
            
            # Add road state malus from previous day (if any)
            instant_reasons = self._entry.runtime_data["score_entity"].extra_state_attributes.get("reasons", [])
            for reason in instant_reasons:
                if "Road state:" in reason:
                    if "(-0.5)" in reason:
                        score += -0.5
                        reasons.append(f"Previous day: {reason}")
                    elif "(-1.0)" in reason:
                        score += -1.0
                        reasons.append(f"Previous day: {reason}")
            
            # Check for night mode at return time
            sun_state = self._hass.states.get("sun.sun")
            if sun_state:
                next_rising = sun_state.attributes.get("next_rising")
                next_setting = sun_state.attributes.get("next_setting")
                if next_rising and next_setting:
                    try:
                        rising_time = datetime.fromisoformat(next_rising).time()
                        setting_time = datetime.fromisoformat(next_setting).time()
                        return_time = datetime.strptime(return_time_str, "%H:%M").time()
                        if setting_time <= return_time or return_time <= rising_time:
                            score += NIGHT_MODE_MALUS
                            reasons.append(f"Trip at night ({NIGHT_MODE_MALUS})")
                    except (ValueError, TypeError):
                        _LOGGER.warning("Failed to parse sun times for trip night check")
            
            # Store reasons in attributes
            final_score = round(max(0, min(10, score)), 1)
            
            self._attr_extra_state_attributes = {
                "reasons": reasons if reasons else ["Good conditions"],
                "office_location": office_weather_entity,
                "home_location": home_weather_entity,
            }
            
            return final_score
            
        except Exception as e:
            _LOGGER.error("Error calculating trip score (return): %s", e)
            return None
    
    @property
    def extra_state_attributes(self):
        """Return extra state attributes with trip details."""
        return self._attr_extra_state_attributes


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
        self._attr_device_info = _create_device_info(entry)

    @property
    def native_value(self):
        """Return status based on trip score go."""
        try:
            trip_score_go = self._entry.runtime_data.get("trip_score_go")
            if not trip_score_go:
                return "analyzing"
            
            score = trip_score_go.native_value
            
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
        self._attr_device_info = _create_device_info(entry)

    @property
    def native_value(self):
        """Return status based on trip score return."""
        try:
            trip_score_return = self._entry.runtime_data.get("trip_score_return")
            if not trip_score_return:
                return "analyzing"
            
            score = trip_score_return.native_value
            
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
        self._attr_device_info = _create_device_info(entry)

    @property
    def native_value(self):
        """Return all reasons affecting the outbound trip score with total malus."""
        try:
            trip_score_go = self._entry.runtime_data.get("trip_score_go")
            instant_score_entity = self._entry.runtime_data["score_entity"]
            if not trip_score_go:
                return "Analyzing..."
            
            reasons = trip_score_go.extra_state_attributes.get("reasons", [])
            score = trip_score_go.native_value
            
            if not reasons or score is None:
                return "Good conditions"
            
            # Total malus from perfect score (10.0)
            total_malus = 10.0 - score
            
            # Show all factors exhaustively
            return f"{' + '.join(reasons)} = -{total_malus:.1f}"
            
        except Exception as e:
            _LOGGER.error("Error calculating trip reasoning (go): %s", e)
            return "Calculating..."

    @property
    def extra_state_attributes(self):
        """Return detailed breakdown of all factors affecting the trip score."""
        try:
            trip_score_go = self._entry.runtime_data.get("trip_score_go")
            instant_score_entity = self._entry.runtime_data["score_entity"]
            if not trip_score_go:
                return {}
            
            score = trip_score_go.native_value
            total_malus = (10.0 - score) if score is not None else 0.0
            
            return {
                "all_factors": trip_score_go.extra_state_attributes.get("reasons", []),
                "total_malus": round(total_malus, 1),
                "home_location": trip_score_go.extra_state_attributes.get("home_location", "unknown"),
                "office_location": trip_score_go.extra_state_attributes.get("office_location", "unknown"),
            }
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
        self._attr_device_info = _create_device_info(entry)

    @property
    def native_value(self):
        """Return all reasons affecting the return trip score with total malus."""
        try:
            trip_score_return = self._entry.runtime_data.get("trip_score_return")
            instant_score_entity = self._entry.runtime_data["score_entity"]
            if not trip_score_return:
                return "Analyzing..."
            
            reasons = trip_score_return.extra_state_attributes.get("reasons", [])
            score = trip_score_return.native_value
            
            if score is None:
                return "Good conditions"
            
            # Total malus from perfect score (10.0)
            total_malus = 10.0 - score
            
            # Show all factors exhaustively
            return f"{' + '.join(reasons)} = -{total_malus:.1f}"
            
        except Exception as e:
            _LOGGER.error("Error calculating trip reasoning (return): %s", e)
            return "Calculating..."

    @property
    def extra_state_attributes(self):
        """Return detailed breakdown of all factors affecting the trip score."""
        try:
            trip_score_return = self._entry.runtime_data.get("trip_score_return")
            instant_score_entity = self._entry.runtime_data["score_entity"]
            if not trip_score_return:
                return {}
            
            score = trip_score_return.native_value
            total_malus = (10.0 - score) if score is not None else 0.0
            
            return {
                "all_factors": trip_score_return.extra_state_attributes.get("reasons", []),
                "total_malus": round(total_malus, 1),
                "office_location": trip_score_return.extra_state_attributes.get("office_location", "unknown"),
                "home_location": trip_score_return.extra_state_attributes.get("home_location", "unknown"),
            }
        except Exception:
            return {}
