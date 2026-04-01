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
                
                # --- SECTION 3: MALUS SENSITIVITY RATIOS (Optional, Advanced) ---
                vol.Optional(CONF_RAIN_RATIO, default=DEFAULT_RAIN_RATIO): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=5.0)),
                vol.Optional(CONF_FOG_RATIO, default=DEFAULT_FOG_RATIO): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=5.0)),
                vol.Optional(CONF_CLOUDY_RATIO, default=DEFAULT_CLOUDY_RATIO): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=5.0)),
                vol.Optional(CONF_COLD_RATIO, default=DEFAULT_COLD_RATIO): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=5.0)),
                vol.Optional(CONF_HOT_RATIO, default=DEFAULT_HOT_RATIO): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=5.0)),
                vol.Optional(CONF_WIND_RATIO, default=DEFAULT_WIND_RATIO): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=5.0)),
                vol.Optional(CONF_HUMIDITY_RATIO, default=DEFAULT_HUMIDITY_RATIO): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=5.0)),
                vol.Optional(CONF_NIGHT_RATIO, default=DEFAULT_NIGHT_RATIO): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=5.0)),
                vol.Optional(CONF_ROAD_STATE_RATIO, default=DEFAULT_ROAD_STATE_RATIO): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=5.0)),
                
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


class BikerSentinelOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for BikerSentinel integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options for the custom component."""
        if user_input is not None:
            # Update the config entry with new ratio values
            return self.async_create_entry(title="", data=user_input)

        # Get current values from config entry data
        current_rain_ratio = DEFAULT_RAIN_RATIO
        current_fog_ratio = DEFAULT_FOG_RATIO
        current_cloudy_ratio = DEFAULT_CLOUDY_RATIO
        current_cold_ratio = DEFAULT_COLD_RATIO
        current_hot_ratio = DEFAULT_HOT_RATIO
        current_wind_ratio = DEFAULT_WIND_RATIO
        current_humidity_ratio = DEFAULT_HUMIDITY_RATIO
        current_night_ratio = DEFAULT_NIGHT_RATIO
        current_road_state_ratio = DEFAULT_ROAD_STATE_RATIO

        # Try to get current values from config entry if available
        try:
            if hasattr(self, 'config_entry') and self.config_entry:
                current_rain_ratio = self.config_entry.data.get(CONF_RAIN_RATIO, DEFAULT_RAIN_RATIO)
                current_fog_ratio = self.config_entry.data.get(CONF_FOG_RATIO, DEFAULT_FOG_RATIO)
                current_cloudy_ratio = self.config_entry.data.get(CONF_CLOUDY_RATIO, DEFAULT_CLOUDY_RATIO)
                current_cold_ratio = self.config_entry.data.get(CONF_COLD_RATIO, DEFAULT_COLD_RATIO)
                current_hot_ratio = self.config_entry.data.get(CONF_HOT_RATIO, DEFAULT_HOT_RATIO)
                current_wind_ratio = self.config_entry.data.get(CONF_WIND_RATIO, DEFAULT_WIND_RATIO)
                current_humidity_ratio = self.config_entry.data.get(CONF_HUMIDITY_RATIO, DEFAULT_HUMIDITY_RATIO)
                current_night_ratio = self.config_entry.data.get(CONF_NIGHT_RATIO, DEFAULT_NIGHT_RATIO)
                current_road_state_ratio = self.config_entry.data.get(CONF_ROAD_STATE_RATIO, DEFAULT_ROAD_STATE_RATIO)
        except Exception:
            # If config_entry is not available, use defaults
            pass

        # Create the options schema with current values as defaults
        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_RAIN_RATIO,
                    default=current_rain_ratio,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0, max=5.0, step=0.1, mode=selector.NumberSelectorMode.SLIDER
                    )
                ),
                vol.Optional(
                    CONF_FOG_RATIO,
                    default=current_fog_ratio,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0, max=5.0, step=0.1, mode=selector.NumberSelectorMode.SLIDER
                    )
                ),
                vol.Optional(
                    CONF_CLOUDY_RATIO,
                    default=current_cloudy_ratio,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0, max=5.0, step=0.1, mode=selector.NumberSelectorMode.SLIDER
                    )
                ),
                vol.Optional(
                    CONF_COLD_RATIO,
                    default=current_cold_ratio,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0, max=5.0, step=0.1, mode=selector.NumberSelectorMode.SLIDER
                    )
                ),
                vol.Optional(
                    CONF_HOT_RATIO,
                    default=current_hot_ratio,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0, max=5.0, step=0.1, mode=selector.NumberSelectorMode.SLIDER
                    )
                ),
                vol.Optional(
                    CONF_WIND_RATIO,
                    default=current_wind_ratio,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0, max=5.0, step=0.1, mode=selector.NumberSelectorMode.SLIDER
                    )
                ),
                vol.Optional(
                    CONF_HUMIDITY_RATIO,
                    default=current_humidity_ratio,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0, max=5.0, step=0.1, mode=selector.NumberSelectorMode.SLIDER
                    )
                ),
                vol.Optional(
                    CONF_NIGHT_RATIO,
                    default=current_night_ratio,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0, max=5.0, step=0.1, mode=selector.NumberSelectorMode.SLIDER
                    )
                ),
                vol.Optional(
                    CONF_ROAD_STATE_RATIO,
                    default=current_road_state_ratio,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0, max=5.0, step=0.1, mode=selector.NumberSelectorMode.SLIDER
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )