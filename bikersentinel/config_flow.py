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
    DEFAULT_HEIGHT_CM,
    DEFAULT_WEIGHT_KG,
    DEFAULT_BIKE_TYPE,
    DEFAULT_EQUIPMENT,
    DEFAULT_SENSITIVITY,
    DEFAULT_RIDING_CONTEXT,
    CONF_SENSOR_TEMP,
    CONF_SENSOR_WIND,
    CONF_SENSOR_RAIN,
    CONF_WEATHER_ENTITY,
    CONF_TRIP_ENABLED,
    CONF_TRIP_HOME_WEATHER,
    CONF_TRIP_OFFICE_WEATHER,
    CONF_TRIP_DEPART_TIME,
    CONF_TRIP_RETURN_TIME,
)

_LOGGER = logging.getLogger(__name__)

class BikerSentinelConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BikerSentinel."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial configuration (Sensors + Rider Profile)."""
        if user_input is not None:
            # Check if user wants to configure trips
            if user_input.get(CONF_TRIP_ENABLED):
                # Save data and continue to trips step
                self._data = user_input
                return await self.async_step_trips()
            else:
                # No trips, create entry
                return self.async_create_entry(
                    title=f"BikerSentinel ({user_input[CONF_BIKE_TYPE]})", 
                    data=user_input
                )

        # Main configuration schema - Sensors & Rider Profile
        data_schema = vol.Schema(
            {
                # --- SECTION 1: WEATHER SENSORS (Required) ---
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
                
                # --- SECTION 2: RIDER PROFILE (Required) ---
                vol.Optional(CONF_HEIGHT, default=DEFAULT_HEIGHT_CM): vol.All(vol.Coerce(int), vol.Range(min=100, max=250)),
                vol.Optional(CONF_WEIGHT, default=DEFAULT_WEIGHT_KG): int,
                vol.Required(CONF_BIKE_TYPE, default=DEFAULT_BIKE_TYPE): vol.In(MACHINE_TYPES),
                vol.Required(CONF_EQUIPMENT, default=DEFAULT_EQUIPMENT): vol.In(EQUIPMENT_LEVELS),
                vol.Required(CONF_RIDING_CONTEXT, default=DEFAULT_RIDING_CONTEXT): vol.In(RIDING_CONTEXTS.keys()),
                vol.Required(CONF_SENSITIVITY, default=DEFAULT_SENSITIVITY): vol.All(vol.Coerce(int), vol.Range(min=1, max=5)),
                
                # --- OPTIONAL: TRIP FORECASTING ---
                vol.Required(CONF_TRIP_ENABLED, default=False): bool,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
        )

    async def async_step_trips(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure trip forecasting (Outbound & Return journeys)."""
        if user_input is not None:
            # Merge trip config with main data
            config_data = {**self._data, **user_input}
            return self.async_create_entry(
                title=f"BikerSentinel ({self._data[CONF_BIKE_TYPE]})", 
                data=config_data
            )

        # Trip configuration schema
        trips_schema = vol.Schema(
            {
                # --- OUTBOUND TRIP (Home → Office) ---
                vol.Required(CONF_TRIP_HOME_WEATHER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="weather")
                ),
                vol.Required(CONF_TRIP_DEPART_TIME): str,  # Format: "HH:MM"
                
                # --- RETURN TRIP (Office → Home) ---
                vol.Required(CONF_TRIP_OFFICE_WEATHER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="weather")
                ),
                vol.Required(CONF_TRIP_RETURN_TIME): str,  # Format: "HH:MM"
            }
        )

        return self.async_show_form(
            step_id="trips",
            data_schema=trips_schema,
        )