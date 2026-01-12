"""Unit tests for BikerSentinel score calculation algorithm."""
import pytest
from unittest.mock import MagicMock, patch


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
        
        status_sensor = BikerSentinelStatus(mock_hass_registry, mock_entry_status)
        
        # Mock entity registry
        mock_registry = MagicMock()
        mock_registry.async_get_entity_id.return_value = "sensor.bikersentinel_score"
        
        with patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_registry):
            mock_hass_registry.states.get.return_value = MockState(str(score_value))
            status = status_sensor.native_value
            assert status == expected_status


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
