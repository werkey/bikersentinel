import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import DOMAIN, MACHINE_TYPES, CONF_TAILLE, CONF_POIDS, CONF_MACHINE_TYPE

class BikerSentinelConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="BikerSentinel", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_TAILLE, default=180): int,
                vol.Required(CONF_POIDS, default=80): int,
                vol.Required(CONF_MACHINE_TYPE, default="Roadster"): vol.In(MACHINE_TYPES),
                vol.Required("sensor_temp"): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Required("sensor_vent"): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Required("sensor_pluie"): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional("weather_entity"): selector.EntitySelector(selector.EntitySelectorConfig(domain="weather")),
            })
        )