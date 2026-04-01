"""The BikerSentinel integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BikerSentinel from a config entry."""
    # Register config service as workaround
    if "bikersentinel_config_service" not in hass.data:
        from .sensor import BikerSentinelConfigService
        service = BikerSentinelConfigService(hass)
        service.register()
        hass.data["bikersentinel_config_service"] = service
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_get_options_flow(config_entry: ConfigEntry):
    """Get the options flow for this handler."""
    _LOGGER.warning("[BikerSentinel] async_get_options_flow called for entry: %s", getattr(config_entry, 'entry_id', config_entry))
    from .config_flow import BikerSentinelOptionsFlowHandler
    return BikerSentinelOptionsFlowHandler()