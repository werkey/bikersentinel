"""Initialisation de l'intégration BikerSentinel."""
import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

# Liste des plateformes à charger (ici uniquement nos sensors)
PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configuration de l'intégration après validation du formulaire."""
    
    # On enregistre les plateformes (le fichier sensor.py)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Déchargement de l'intégration (si on la supprime)."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)