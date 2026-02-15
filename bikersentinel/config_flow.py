"""Config flow for BikerSentinel integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    MACHINE_TYPES,
    EQUIPMENT_LEVELS,
    RIDING_CONTEXTS,
    CONF_HEIGHT,
    CONF_WEIGHT,
    CONF_BIKE_TYPE,
    CONF_EQUIPMENT,
    CONF_SENSITIVITY,
    CONF_RIDING_CONTEXT,
    DEFAULT_BIKE_TYPE,
    DEFAULT_EQUIPMENT,
    DEFAULT_SENSITIVITY,
    DEFAULT_RIDING_CONTEXT,
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
    CONF_SOLAR_BLINDNESS_ENABLED,
    CONF_COMMUTE_ALERT_ENABLED,
    CONF_COMMUTE_DEPARTURE_TIME,
    CONF_COMMUTE_ALERT_ADVANCE,
)

_LOGGER = logging.getLogger(__name__)

class BikerSentinelConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BikerSentinel."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            # Use the bike type in the title to distinguish multiple instances
            return self.async_create_entry(title=f"BikerSentinel ({user_input[CONF_BIKE_TYPE]})", data=user_input)

        # Schema definition using English constants
        data_schema = vol.Schema(
            {
                # Optional Physical Attributes
                vol.Optional(CONF_HEIGHT): int,
                vol.Optional(CONF_WEIGHT): int,
                
                # Sensitivity Slider (1-5)
                vol.Required(CONF_SENSITIVITY, default=DEFAULT_SENSITIVITY): vol.All(vol.Coerce(int), vol.Range(min=1, max=5)),

                # Machine & Gear
                vol.Required(CONF_BIKE_TYPE, default=DEFAULT_BIKE_TYPE): vol.In(MACHINE_TYPES),
                vol.Required(CONF_EQUIPMENT, default=DEFAULT_EQUIPMENT): vol.In(EQUIPMENT_LEVELS),
                vol.Required(CONF_RIDING_CONTEXT, default=DEFAULT_RIDING_CONTEXT): vol.In(RIDING_CONTEXTS.keys()),
                
                # Sensors Selection
                vol.Required(CONF_SENSOR_TEMP): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_SENSOR_WIND): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_SENSOR_RAIN): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_WEATHER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="weather")
                ),
                
                # Night Mode & Features
                vol.Required(CONF_NIGHT_MODE_ENABLED, default=True): bool,
                vol.Required(CONF_PRECIP_HISTORY_ENABLED, default=True): bool,
                vol.Required(CONF_TEMP_HUMIDITY_TRENDS_ENABLED, default=True): bool,
                
                # Trip Score Configuration (Optional)
                vol.Required(CONF_TRIP_ENABLED, default=False): bool,
                vol.Optional(CONF_TRIP_WEATHER_START): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="weather")
                ),
                vol.Optional(CONF_TRIP_WEATHER_END): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="weather")
                ),
                vol.Optional(CONF_TRIP_DEPART_TIME): str,  # Format: "HH:MM"
                vol.Optional(CONF_TRIP_RETURN_TIME): str,  # Format: "HH:MM"
                
                # Solar Blindness (Glare Alert)
                vol.Required(CONF_SOLAR_BLINDNESS_ENABLED, default=True): bool,
                
                # Commute Alert Configuration
                vol.Required(CONF_COMMUTE_ALERT_ENABLED, default=False): bool,
                vol.Optional(CONF_COMMUTE_DEPARTURE_TIME): str,  # Format: "HH:MM"
                vol.Optional(CONF_COMMUTE_ALERT_ADVANCE, default=15): int,  # Minutes
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
        )