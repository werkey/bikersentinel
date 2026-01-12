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
from homeassistant.helpers import entity_registry

from .const import (
    DOMAIN,
    PROTECTION_COEFS,
    EQUIPMENT_COEFS,
    RIDING_CONTEXTS,
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

    # Add the 3 entities
    async_add_entities(
        [
            BikerSentinelScore(hass, entry, height, weight, bike_type, equipment, sensitivity, riding_context),
            BikerSentinelStatus(hass, entry),
            BikerSentinelReasoning(hass, entry),
        ],
        True,
    )


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

    def __init__(self, hass, entry):
        self._hass = hass
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._score_unique_id = f"{entry.entry_id}_score"
        self._attr_options = ["optimal", "favorable", "degraded", "critical", "dangerous", "analyzing", "error"]

    @property
    def native_value(self):
        # CORRECTED: Use entity_registry to safely get the ID
        registry = entity_registry.async_get(self._hass)
        score_entity_id = registry.async_get_entity_id("sensor", DOMAIN, self._score_unique_id)
        
        if not score_entity_id: return "analyzing"

        s_state = self._hass.states.get(score_entity_id)
        if not s_state or s_state.state in ["unknown", "unavailable", None]: return "analyzing"
            
        try:
            s = float(s_state.state)
            if s >= 9: return "optimal"
            if s >= 7: return "favorable"
            if s >= 5: return "degraded"
            if s >= 3: return "critical"
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
        self._attr_unique_id = f"{entry.entry_id}_reasoning"
        self._score_unique_id = f"{entry.entry_id}_score"

    @property
    def native_value(self):
        """Reads the 'reasons' attribute from the Score entity."""
        # CORRECTED: Use entity_registry to safely get the ID
        registry = entity_registry.async_get(self._hass)
        score_entity_id = registry.async_get_entity_id("sensor", DOMAIN, self._score_unique_id)
        
        if not score_entity_id: return "Initializing..."
        
        s_state = self._hass.states.get(score_entity_id)
        if not s_state: return "Waiting..."
        
        # Access attributes safely
        reasons = s_state.attributes.get("reasons", [])
        
        if not reasons: return "RAS"
        return ", ".join(reasons)