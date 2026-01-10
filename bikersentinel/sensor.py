import logging
from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN, PROTECTION_COEFS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Configuration des capteurs."""
    taille = entry.data.get("taille", 180)
    poids = entry.data.get("poids", 80)
    machine = entry.data.get("type_moto", "Roadster")

    # On ajoute les deux capteurs d'un coup
    async_add_entities([
        BikerSentinelScore(hass, entry, taille, poids, machine),
        BikerSentinelStatus(hass, entry)
    ], True)

class BikerSentinelScore(SensorEntity):
    """Capteur de Score."""
    def __init__(self, hass, entry, taille, poids, machine):
        self._hass = hass
        self._attr_name = "BikerSentinel Score"
        self._attr_unique_id = f"{entry.entry_id}_score"
        self._attr_native_unit_of_measurement = "/10"
        self._attr_icon = "mdi:motorbike"
        
        # Récupération des IDs des capteurs choisis
        self._ent_temp = entry.data.get("sensor_temp")
        self._ent_vent = entry.data.get("sensor_vent")
        self._ent_pluie = entry.data.get("sensor_pluie")
        self._ent_weather = entry.data.get("weather_entity")
        
        # Calcul des constantes pilotes
        self._coef = PROTECTION_COEFS.get(machine, 1.2)
        self._surface = (taille * 0.005) + (poids * 0.002)

    @property
    def native_value(self):
        try:
            # Récupération sécurisée des états
            s_temp = self._hass.states.get(self._ent_temp)
            s_vent = self._hass.states.get(self._ent_vent)
            s_pluie = self._hass.states.get(self._ent_pluie)
            
            if not s_temp or not s_vent or not s_pluie:
                return None

            t = float(s_temp.state)
            v = float(s_vent.state)
            p = float(s_pluie.state)
            
            # Météo globale
            weather_state = "clear"
            if self._ent_weather:
                w_state = self._hass.states.get(self._ent_weather)
                if w_state:
                    weather_state = w_state.state

            # 1. VÉTOS SÉCURITÉ (Score 0 immédiat)
            if weather_state in ["snowy", "snowy-rainy", "hail", "lightning-rainy"] or t < 1 or v > 85 or p > 10:
                return 0.0

            score = 10.0

            # 2. MALUS VISIBILITÉ
            if weather_state == "fog":
                score -= 3.0

            # 3. CALCUL FROID (Windchill + Morphologie)
            t_ressentie = t - (v * 0.2 * self._coef)
            if t_ressentie < 15:
                malus_froid = (15 - t_ressentie) * 0.4 * (self._surface / 1.0)
                score -= malus_froid

            # 4. MALUS VENT (Stabilité)
            if v > 35:
                malus_vent = (v - 35) * 0.15 * self._coef
                score -= malus_vent

            # 5. MALUS PLUIE
            if p > 0:
                score -= 3.0

            return round(max(0, min(10, score)), 1)
        except Exception as e:
            _LOGGER.error("Erreur calcul BikerSentinel: %s", e)
            return None

class BikerSentinelStatus(SensorEntity):
    """Capteur de Statut (Texte)."""
    def __init__(self, hass, entry):
        self._hass = hass
        self._attr_name = "BikerSentinel Statut"
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_icon = "mdi:shield-check"

    @property
    def native_value(self):
        # On cherche l'entité score pour définir le statut
        # Astuce : On utilise l'ID que HA va générer
        score_id = "sensor.bikersentinel_score"
        s_state = self._hass.states.get(score_id)
        
        if not s_state or s_state.state in ["unknown", "unavailable"]:
            return "Analyse..."
            
        try:
            s = float(s_state.state)
            if s >= 9: return "Optimal"
            if s >= 7: return "Favorable"
            if s >= 5: return "Dégradé"
            if s >= 3: return "Critique"
            return "Dangereux"
        except:
            return "Erreur"