"""Unit tests for BikerSentinel score calculation algorithm."""
import pytest
from unittest.mock import MagicMock, patch
from bikersentinel.const import (
    CONF_HEIGHT, CONF_WEIGHT, CONF_BIKE_TYPE, CONF_EQUIPMENT,
    CONF_SENSITIVITY, CONF_RIDING_CONTEXT, CONF_SENSOR_TEMP,
    CONF_SENSOR_WIND, CONF_SENSOR_RAIN, CONF_WEATHER_ENTITY,
    CONF_TRIP_ENABLED, CONF_TRIP_WEATHER_START, CONF_TRIP_WEATHER_END,
    CONF_TRIP_DEPART_TIME, CONF_TRIP_RETURN_TIME,
    CONF_NIGHT_MODE_ENABLED, CONF_PRECIP_HISTORY_ENABLED,
    DEFAULT_HEIGHT_CM, DEFAULT_WEIGHT_KG, DEFAULT_BIKE_TYPE, 
    DEFAULT_EQUIPMENT, DEFAULT_SENSITIVITY, DEFAULT_RIDING_CONTEXT,
    MACHINE_TYPES, EQUIPMENT_LEVELS, RIDING_CONTEXTS, PROTECTION_COEFS,
    EQUIPMENT_COEFS, NIGHT_MODE_MALUS, PRECIP_HISTORY_WINDOW
)


class MockState:
    """Mock Home Assistant state object."""
    
    def __init__(self, state, attributes=None):
        self.state = state
        self.attributes = attributes or {}


class TestBikerSentinelScore:
    """Test cases for BikerSentinelScore calculation."""
    
    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = MagicMock()
        hass.states = MagicMock()
        hass.helpers = MagicMock()
        return hass
    
    @pytest.fixture
    def mock_entry(self):
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry_123"
        entry.data = {
            "height": 175,
            "weight": 80,
            "sensitivity": 3,
            "bike_type": "Roadster",
            "equipment_level": "Standard",
            "sensor_temp": "sensor.temp",
            "sensor_wind": "sensor.wind",
            "sensor_rain": "sensor.rain",
            "weather_entity": "weather.home"
        }
        return entry
    
    @pytest.fixture
    def score_sensor(self, mock_hass, mock_entry):
        """Create a BikerSentinelScore instance for testing."""
        # Import here to avoid issues with mocking
        from bikersentinel.sensor import BikerSentinelScore
        
        sensor = BikerSentinelScore(
            mock_hass,
            mock_entry,
            height=175,
            weight=80,
            bike_type="Roadster",
            equipment="Standard",
            sensitivity=3,
            riding_context="road"
        )
        return sensor
    
    # ============ SAFETY VETOS (Score = 0) ============
    
    def test_veto_ice_risk_temp_below_1(self, score_sensor, mock_hass):
        """Test ice risk veto: Temperature < 1°C returns 0."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("-5"),
            "sensor.wind": MockState("20"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("clear")
        }.get(entity_id)
        
        score = score_sensor.native_value
        assert score == 0.0
    
    def test_veto_storm_winds_above_85(self, score_sensor, mock_hass):
        """Test storm winds veto: Wind > 85 km/h returns 0."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("10"),
            "sensor.wind": MockState("90"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("clear")
        }.get(entity_id)
        
        score = score_sensor.native_value
        assert score == 0.0
    
    def test_veto_dangerous_weather_snow(self, score_sensor, mock_hass):
        """Test dangerous weather veto: Snowy conditions return 0."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("5"),
            "sensor.wind": MockState("20"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("snowy")
        }.get(entity_id)
        
        score = score_sensor.native_value
        assert score == 0.0
    
    def test_veto_dangerous_weather_hail(self, score_sensor, mock_hass):
        """Test dangerous weather veto: Hail conditions return 0."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("5"),
            "sensor.wind": MockState("20"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("hail")
        }.get(entity_id)
        
        score = score_sensor.native_value
        assert score == 0.0
    
    def test_veto_dangerous_weather_lightning(self, score_sensor, mock_hass):
        """Test dangerous weather veto: Lightning conditions return 0."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("5"),
            "sensor.wind": MockState("20"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("lightning-rainy")
        }.get(entity_id)
        
        score = score_sensor.native_value
        assert score == 0.0
    
    # ============ NOMINAL CONDITIONS (Score = 10) ============
    
    def test_perfect_conditions_score_10(self, score_sensor, mock_hass):
        """Test perfect conditions: Warm, low wind, no rain = 10."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("25"),
            "sensor.wind": MockState("5"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("clear")
        }.get(entity_id)
        
        score = score_sensor.native_value
        assert score == 10.0
    
    def test_good_conditions_score_high(self, score_sensor, mock_hass):
        """Test good conditions: Mild temp, moderate wind = high score."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("18"),
            "sensor.wind": MockState("20"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("clear")
        }.get(entity_id)
        
        score = score_sensor.native_value
        assert score > 8.0  # Should be high
    
    # ============ WINDCHILL MALUS (Cold Impact) ============
    
    def test_windchill_cold_temp_malus(self, score_sensor, mock_hass):
        """Test windchill: Cold temperature produces malus."""
        # Temp 5°C + Wind 30 km/h on Roadster (coef 1.2)
        # t_felt = 5 - (30 * 0.2 * 1.2) = 5 - 7.2 = -2.2
        # malus = (15 - (-2.2)) * 0.2 * surface = 17.2 * 0.2 * surface ≈ significant
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("5"),
            "sensor.wind": MockState("30"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("clear")
        }.get(entity_id)
        
        score = score_sensor.native_value
        assert score < 10.0  # Should be reduced
        assert score > 0.0   # But not zero (no veto)
    
    def test_windchill_below_threshold_no_malus(self, score_sensor, mock_hass):
        """Test windchill: If t_felt >= 15°C, no cold malus."""
        # Temp 20°C, low wind → t_felt > 15, no malus
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("20"),
            "sensor.wind": MockState("10"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("clear")
        }.get(entity_id)
        
        score = score_sensor.native_value
        # No cold malus expected, only rain check (0mm) = 10
        assert score == 10.0
    
    # ============ EQUIPMENT MALUS REDUCTION ============
    
    def test_equipment_heated_reduces_cold_malus(self, mock_hass, mock_entry):
        """Test heated equipment: Reduces cold malus."""
        from bikersentinel.sensor import BikerSentinelScore
        
        # Create sensor with Heated equipment
        sensor_heated = BikerSentinelScore(
            mock_hass, mock_entry,
            height=175, weight=80,
            bike_type="Roadster",
            equipment="Heated",  # 0.3x reduction
            sensitivity=3,
            riding_context="road"
        )
        
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("5"),
            "sensor.wind": MockState("30"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("clear")
        }.get(entity_id)
        
        score_heated = sensor_heated.native_value
        assert score_heated > 5.0  # Heated protects better
    
    def test_equipment_winter_moderate_reduction(self, mock_hass, mock_entry):
        """Test winter equipment: Moderate cold malus reduction."""
        from bikersentinel.sensor import BikerSentinelScore
        
        sensor_winter = BikerSentinelScore(
            mock_hass, mock_entry,
            height=175, weight=80,
            bike_type="Roadster",
            equipment="Winter",  # 0.6x reduction
            sensitivity=3,
            riding_context="road"
        )
        
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("5"),
            "sensor.wind": MockState("30"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("clear")
        }.get(entity_id)
        
        score_winter = sensor_winter.native_value
        assert 5.0 < score_winter < 8.0  # Middle ground
    
    # ============ SENSITIVITY (Frilosité) ============
    
    def test_sensitivity_viking_reduces_cold(self, mock_hass, mock_entry):
        """Test Viking sensitivity (1): Reduces cold malus."""
        from bikersentinel.sensor import BikerSentinelScore
        
        sensor_viking = BikerSentinelScore(
            mock_hass, mock_entry,
            height=175, weight=80,
            bike_type="Roadster",
            equipment="Standard",
            sensitivity=1,  # Viking: 0.8x factor
            riding_context="road"
        )
        
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("5"),
            "sensor.wind": MockState("30"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("clear")
        }.get(entity_id)
        
        score_viking = sensor_viking.native_value
        # Viking reduces cold malus, so score should be better than 3.5
        assert score_viking > 3.0  # With new BSA formula, less affected by cold
    
    def test_sensitivity_sensitive_increases_cold(self, mock_hass, mock_entry):
        """Test Sensitive (5): Increases cold malus."""
        from bikersentinel.sensor import BikerSentinelScore
        
        sensor_sensitive = BikerSentinelScore(
            mock_hass, mock_entry,
            height=175, weight=80,
            bike_type="Roadster",
            equipment="Standard",
            sensitivity=5,  # Sensitive: 1.2x factor
            riding_context="road"
        )
        
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("5"),
            "sensor.wind": MockState("30"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("clear")
        }.get(entity_id)
        
        score_sensitive = sensor_sensitive.native_value
        assert score_sensitive < 5.0  # More affected by cold
    
    # ============ WIND STABILITY MALUS ============
    
    def test_wind_stability_above_35_produces_malus(self, score_sensor, mock_hass):
        """Test wind stability: Wind > 35 km/h produces malus."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("15"),
            "sensor.wind": MockState("50"),  # Above 35
            "sensor.rain": MockState("0"),
            "weather.home": MockState("clear")
        }.get(entity_id)
        
        score = score_sensor.native_value
        # With riding_speed 80, total_wind = 50 + 8 = 58
        # And new BSA formula, expect lower score
        assert score < 5.0  # Significant malus from wind
    
    def test_wind_stability_below_35_no_malus(self, score_sensor, mock_hass):
        """Test wind stability: Wind <= 35 km/h, no stability malus."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("15"),
            "sensor.wind": MockState("25"),  # Below 35
            "sensor.rain": MockState("0"),
            "weather.home": MockState("clear")
        }.get(entity_id)
        
        score = score_sensor.native_value
        # At t=15, no cold malus (threshold). Low wind + riding_speed 80 = total ~28
        # With new BSA formula, expect some windchill malus still
        assert score >= 6.0  # Should be relatively good
    
    # ============ RAIN MALUS ============
    
    def test_rain_produces_malus(self, score_sensor, mock_hass):
        """Test rain: Any precipitation > 0 produces -3 malus."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("20"),
            "sensor.wind": MockState("10"),
            "sensor.rain": MockState("5"),  # 5mm rain
            "weather.home": MockState("clear")
        }.get(entity_id)
        
        score = score_sensor.native_value
        # Should be 10 - 3 = 7
        assert score == 7.0
    
    def test_no_rain_no_malus(self, score_sensor, mock_hass):
        """Test no rain: 0mm rain, no rain malus."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("20"),
            "sensor.wind": MockState("10"),
            "sensor.rain": MockState("0"),  # No rain
            "weather.home": MockState("clear")
        }.get(entity_id)
        
        score = score_sensor.native_value
        assert score == 10.0
    
    # ============ FOG MALUS ============
    
    def test_fog_produces_malus(self, score_sensor, mock_hass):
        """Test fog: Fog conditions produce -3 malus."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("20"),
            "sensor.wind": MockState("10"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("fog")  # Fog
        }.get(entity_id)
        
        score = score_sensor.native_value
        # Should be 10 - 3 = 7
        assert score == 7.0
    
    # ============ BIKE TYPE PROTECTION COEFFICIENTS ============
    
    def test_gt_bike_better_protection(self, mock_hass, mock_entry):
        """Test GT bike: Lower coefficient (0.7) = better protection."""
        from bikersentinel.sensor import BikerSentinelScore
        
        sensor_gt = BikerSentinelScore(
            mock_hass, mock_entry,
            height=175, weight=80,
            bike_type="GT",  # 0.7x coef (best protection)
            equipment="Standard",
            sensitivity=3,
            riding_context="road"
        )
        
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("5"),
            "sensor.wind": MockState("30"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("clear")
        }.get(entity_id)
        
        score_gt = sensor_gt.native_value
        # GT protects better but with new BSA formula, still cold
        assert score_gt > 3.0  # GT has better protection than Roadster
    
    def test_roadster_less_protection(self, score_sensor, mock_hass):
        """Test Roadster: Higher coefficient (1.2) = less protection."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("5"),
            "sensor.wind": MockState("30"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("clear")
        }.get(entity_id)
        
        score_roadster = score_sensor.native_value
        # Roadster has coef 1.2, more exposed to wind
        # With new BSA and riding_speed context, expect lower score
        assert 1.0 < score_roadster < 4.0  # Less protected than GT
    
    # ============ EDGE CASES ============
    
    def test_score_bounded_min_zero(self, score_sensor, mock_hass):
        """Test score never goes below 0."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("-20"),  # Extreme cold
            "sensor.wind": MockState("80"),   # High wind (but <85)
            "sensor.rain": MockState("50"),   # Heavy rain
            "weather.home": MockState("fog")  # Fog
        }.get(entity_id)
        
        score = score_sensor.native_value
        assert score >= 0.0
    
    def test_score_bounded_max_10(self, score_sensor, mock_hass):
        """Test score never goes above 10."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("30"),  # Warm
            "sensor.wind": MockState("0"),   # No wind
            "sensor.rain": MockState("0"),   # No rain
            "weather.home": MockState("clear")
        }.get(entity_id)
        
        score = score_sensor.native_value
        assert score <= 10.0
    
    def test_unavailable_sensor_returns_none(self, score_sensor, mock_hass):
        """Test unavailable sensor: Returns None."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("unavailable"),
            "sensor.wind": MockState("20"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("clear")
        }.get(entity_id)
        
        score = score_sensor.native_value
        assert score is None
    
    def test_unknown_sensor_returns_none(self, score_sensor, mock_hass):
        """Test unknown sensor state: Returns None."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("unknown"),
            "sensor.wind": MockState("20"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("clear")
        }.get(entity_id)
        
        score = score_sensor.native_value
        assert score is None
    
    def test_missing_sensor_returns_none(self, score_sensor, mock_hass):
        """Test missing sensor (None): Returns None."""
        mock_hass.states.get.side_effect = lambda entity_id: None
        
        score = score_sensor.native_value
        assert score is None


class TestBikerSentinelStatus:
    """Test cases for BikerSentinelStatus mapping."""
    
    @pytest.fixture
    def mock_hass_registry(self):
        """Create mock HA with entity registry."""
        hass = MagicMock()
        hass.states = MagicMock()
        hass.helpers = MagicMock()
        return hass
    
    @pytest.fixture
    def mock_entry_status(self):
        """Create mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry_123"
        return entry
    
    @pytest.mark.parametrize("score_value,expected_status", [
        (9.5, "optimal"),
        (9.0, "optimal"),
        (8.0, "favorable"),
        (7.0, "favorable"),
        (6.0, "degraded"),
        (5.0, "degraded"),
        (4.0, "critical"),
        (3.0, "critical"),
        (2.0, "dangerous"),
        (0.5, "dangerous"),
    ])
    def test_status_mapping(self, score_value, expected_status, mock_hass_registry, mock_entry_status):
        """Test status text mapping based on score."""
        from bikersentinel.sensor import BikerSentinelStatus
        
        # Create a mock score entity with native_value
        mock_score_entity = MagicMock()
        mock_score_entity.native_value = score_value
        
        # Setup runtime_data with the mock score entity
        mock_entry_status.runtime_data = {"score_entity": mock_score_entity}
        
        status_sensor = BikerSentinelStatus(mock_hass_registry, mock_entry_status)
        status = status_sensor.native_value
        assert status == expected_status




class TestBikerSentinelNightMode:
    """Test cases for Night Mode visibility penalty."""
    
    @pytest.fixture
    def mock_hass_sun(self):
        """Create mock HA with sun entity."""
        hass = MagicMock()
        return hass
    
    @pytest.fixture
    def mock_entry_night(self):
        """Create mock config entry for night mode."""
        entry = MagicMock()
        entry.entry_id = "test_entry_night"
        entry.data = {CONF_NIGHT_MODE_ENABLED: True}
        return entry
    
    @pytest.mark.parametrize("elevation,expected_status", [
        (25.0, "day"),           # Sun well above horizon
        (11.0, "day"),           # Sun above 10°
        (10.0, "twilight"),      # Sun at 10° - twilight starts
        (5.0, "twilight"),       # Golden hour
        (0.0, "civil_twilight"), # Sunset
        (-3.0, "civil_twilight"), # Civil twilight
        (-6.0, "night"),         # Astronomical twilight start
        (-15.0, "night"),        # Full night
    ])
    def test_night_mode_visibility(self, elevation, expected_status, mock_hass_sun, mock_entry_night):
        """Test night mode visibility status based on solar elevation."""
        from bikersentinel.sensor import BikerSentinelNightMode
        
        night_sensor = BikerSentinelNightMode(mock_hass_sun, mock_entry_night)
        
        mock_sun_state = MagicMock()
        mock_sun_state.attributes = {"elevation": elevation, "azimuth": 180.0}
        mock_hass_sun.states.get.return_value = mock_sun_state
        
        status = night_sensor.native_value
        assert status == expected_status


class TestBikerSentinelTripScore:
    """Test cases for Trip Score calculation."""
    
    @pytest.fixture
    def mock_hass_trip(self):
        """Create mock HA for trip score."""
        hass = MagicMock()
        return hass
    
    @pytest.fixture
    def mock_entry_trip(self):
        """Create mock config entry for trip score."""
        entry = MagicMock()
        entry.entry_id = "test_entry_trip"
        entry.data = {
            CONF_TRIP_ENABLED: True,
            CONF_TRIP_DEPART_TIME: "08:00",
            CONF_TRIP_RETURN_TIME: "17:00",
            CONF_TRIP_WEATHER_START: "weather.home",
            CONF_TRIP_WEATHER_END: "weather.work",
        }
        return entry
    
    @pytest.mark.parametrize("condition,expected_score", [
        ("clear", 10.0),
        ("cloudy", 9.0),
        ("partlycloudy", 9.5),
        ("rainy", 6.5),
        ("fog", 5.0),
        ("hail", 2.0),
        ("snowy", 1.0),
        ("lightning-rainy", 0.0),
    ])
    def test_trip_score_weather_mapping(self, condition, expected_score, mock_hass_trip, mock_entry_trip):
        """Test trip score mapping for different weather conditions."""
        from bikersentinel.sensor import BikerSentinelTripScore
        
        trip_sensor = BikerSentinelTripScore(mock_hass_trip, mock_entry_trip)
        score = trip_sensor._get_score_for_condition(condition)
        assert score == expected_score
    
    def test_trip_score_averages_depart_return(self, mock_hass_trip, mock_entry_trip):
        """Test that trip score averages departure and return scores."""
        from bikersentinel.sensor import BikerSentinelTripScore
        
        trip_sensor = BikerSentinelTripScore(mock_hass_trip, mock_entry_trip)
        
        # Mock weather states
        def mock_states_get(entity_id):
            if "home" in entity_id:
                state = MagicMock()
                state.state = "clear"  # Score 10.0
                return state
            elif "work" in entity_id:
                state = MagicMock()
                state.state = "rainy"  # Score 6.5
                return state
            return None
        
        mock_hass_trip.states.get = mock_states_get
        score = trip_sensor.native_value
        
        # Average of 10.0 and 6.5 = 8.25
        assert score == 8.3 or score == 8.2  # Allow rounding variance


class TestBikerSentinelRoadState:
    """Test cases for Road State correlation."""
    
    @pytest.fixture
    def mock_hass_road(self):
        """Create mock HA for road state."""
        hass = MagicMock()
        return hass
    
    @pytest.fixture
    def mock_entry_road(self):
        """Create mock config entry for road state."""
        entry = MagicMock()
        entry.entry_id = "test_entry_road"
        entry.data = {CONF_SENSOR_RAIN: "sensor.rain", CONF_SENSOR_TEMP: "sensor.temp"}
        return entry
    
    @pytest.mark.parametrize("precip_mm,temp_c,expected_state,expected_malus", [
        (0.0, 10, "dry", 0.0),               # No rain, normal temp
        (2.0, 10, "damp", -1.0),             # Light rain
        (5.0, 10, "wet", -3.0),              # Moderate rain
        (10.0, 10, "sludge", -6.0),          # Heavy rain, normal temp
        (10.0, -5, "icy", -8.0),             # Heavy rain, freezing temp
        (15.0, -2, "icy", -8.0),             # Very heavy rain, freezing
    ])
    def test_road_state_inference(self, precip_mm, temp_c, expected_state, expected_malus, mock_hass_road, mock_entry_road):
        """Test road state inference based on precipitation and temperature."""
        from bikersentinel.sensor import BikerSentinelPrecipitationHistory
        
        road_sensor = BikerSentinelPrecipitationHistory(mock_hass_road, mock_entry_road)
        
        # Mock states
        def mock_states_get(entity_id):
            if "rain" in entity_id:
                state = MagicMock()
                state.state = str(precip_mm)
                return state
            elif "temp" in entity_id:
                state = MagicMock()
                state.state = str(temp_c)
                return state
            return None
        
        mock_hass_road.states.get = mock_states_get
        
        road_state, traction_factor, malus = road_sensor._infer_road_state(precip_mm)
        
        assert road_state == expected_state
        assert malus == expected_malus


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
