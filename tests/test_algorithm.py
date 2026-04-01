"""Unit tests for BikerSentinel v2.0 - Refactored Core Algorithm."""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

from bikersentinel.const import (
    CONF_HEIGHT, CONF_WEIGHT, CONF_BIKE_TYPE, CONF_EQUIPMENT,
    CONF_SENSITIVITY, CONF_RIDING_CONTEXT, CONF_SENSOR_TEMP,
    CONF_SENSOR_WIND, CONF_SENSOR_RAIN, CONF_WEATHER_ENTITY,
    CONF_TRIP_ENABLED, CONF_TRIP_HOME_WEATHER, CONF_TRIP_OFFICE_WEATHER,
    CONF_TRIP_DEPART_TIME, CONF_TRIP_RETURN_TIME,
    CONF_RAIN_RATIO, CONF_FOG_RATIO, CONF_CLOUDY_RATIO, CONF_COLD_RATIO,
    CONF_HOT_RATIO, CONF_WIND_RATIO, CONF_HUMIDITY_RATIO, CONF_NIGHT_RATIO, CONF_ROAD_STATE_RATIO,
    DEFAULT_HEIGHT_CM, DEFAULT_WEIGHT_KG, DEFAULT_BIKE_TYPE, 
    DEFAULT_EQUIPMENT, DEFAULT_SENSITIVITY, DEFAULT_RIDING_CONTEXT,
    DEFAULT_RAIN_RATIO, DEFAULT_FOG_RATIO, DEFAULT_CLOUDY_RATIO, DEFAULT_COLD_RATIO,
    DEFAULT_HOT_RATIO, DEFAULT_WIND_RATIO, DEFAULT_HUMIDITY_RATIO, DEFAULT_NIGHT_RATIO, DEFAULT_ROAD_STATE_RATIO,
    MACHINE_TYPES, EQUIPMENT_LEVELS, RIDING_CONTEXTS,
)


class MockState:
    """Mock Home Assistant state object."""
    
    def __init__(self, state, attributes=None):
        self.state = state
        self.attributes = attributes or {}


class TestBikerSentinelScoreCore:
    """Test cases for core BikerSentinelScore calculation."""
    
    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = MagicMock()
        hass.states = MagicMock()
        return hass
    
    @pytest.fixture
    def mock_entry(self):
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry_123"
        entry.data = {
            CONF_HEIGHT: 175,
            CONF_WEIGHT: 80,
            CONF_SENSITIVITY: 3,
            CONF_BIKE_TYPE: "Roadster",
            CONF_EQUIPMENT: "Standard",
            CONF_SENSOR_TEMP: "sensor.temp",
            CONF_SENSOR_WIND: "sensor.wind",
            CONF_SENSOR_RAIN: "sensor.rain",
            CONF_WEATHER_ENTITY: "weather.home",
            CONF_RIDING_CONTEXT: "road",
            CONF_TRIP_ENABLED: False,
            CONF_RAIN_RATIO: DEFAULT_RAIN_RATIO,
            CONF_FOG_RATIO: DEFAULT_FOG_RATIO,
            CONF_CLOUDY_RATIO: DEFAULT_CLOUDY_RATIO,
            CONF_COLD_RATIO: DEFAULT_COLD_RATIO,
            CONF_HOT_RATIO: DEFAULT_HOT_RATIO,
            CONF_WIND_RATIO: DEFAULT_WIND_RATIO,
            CONF_HUMIDITY_RATIO: DEFAULT_HUMIDITY_RATIO,
            CONF_NIGHT_RATIO: DEFAULT_NIGHT_RATIO,
            CONF_ROAD_STATE_RATIO: DEFAULT_ROAD_STATE_RATIO,
        }
        entry.runtime_data = {}
        return entry

    @pytest.fixture
    def score_entity(self, mock_hass, mock_entry):
        """Create a BikerSentinelScore instance."""
        from bikersentinel.sensor import BikerSentinelScore
        return BikerSentinelScore(
            mock_hass, mock_entry,
            height=175, weight=80,
            bike_type="Roadster",
            equipment="Standard",
            sensitivity=3,
            riding_context="road",
            rain_ratio=DEFAULT_RAIN_RATIO,
            fog_ratio=DEFAULT_FOG_RATIO,
            cloudy_ratio=DEFAULT_CLOUDY_RATIO,
            cold_ratio=DEFAULT_COLD_RATIO,
            hot_ratio=DEFAULT_HOT_RATIO,
            wind_ratio=DEFAULT_WIND_RATIO,
            humidity_ratio=DEFAULT_HUMIDITY_RATIO,
            night_ratio=DEFAULT_NIGHT_RATIO,
            road_state_ratio=DEFAULT_ROAD_STATE_RATIO
        )

    def test_score_initialization(self, score_entity):
        """Test that score entity initializes correctly."""
        assert score_entity._attr_unique_id == "test_entry_123_score"
        assert score_entity._riding_context == "road"

    def test_score_perfect_conditions(self, mock_hass, score_entity):
        """Test score with perfect weather conditions (high score expected)."""
        # Mock weather entity with humidity attribute
        weather_state = MockState("sunny", {"humidity": 40})
        
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("20"),
            "sensor.wind": MockState("10"),
            "sensor.rain": MockState("0"),
            "weather.home": weather_state,
            "sun.sun": MockState("above_horizon", {"elevation": 45, "azimuth": 180}),
        }.get(entity_id)
        
        score = score_entity.native_value
        # Score should be relatively high with good conditions
        # Note: Internal calculations may reduce slightly from 10.0
        assert score >= 7.0, f"Expected score >= 7.0 for good conditions, got {score}"

    def test_score_ice_veto(self, mock_hass, score_entity):
        """Test that ice risk triggers immediate 0.0 score."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("0"),  # Ice risk
            "sensor.wind": MockState("10"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("sunny"),
        }.get(entity_id)
        
        score = score_entity.native_value
        assert score == 0.0

    def test_score_dangerous_weather_veto(self, mock_hass, score_entity):
        """Test that dangerous weather triggers immediate 0.0."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("10"),
            "sensor.wind": MockState("10"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("snowy"),  # Dangerous weather
        }.get(entity_id)
        
        score = score_entity.native_value
        assert score == 0.0

    def test_score_high_wind_veto(self, mock_hass, score_entity):
        """Test that extreme winds trigger immediate 0.0."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("15"),
            "sensor.wind": MockState("90"),  # Extreme wind
            "sensor.rain": MockState("0"),
            "weather.home": MockState("sunny"),
        }.get(entity_id)
        
        score = score_entity.native_value
        assert score == 0.0

    def test_score_fog_penalty(self, mock_hass, score_entity):
        """Test fog reduces score by 3.0."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("20"),
            "sensor.wind": MockState("10"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("fog"),  # Fog penalty
        }.get(entity_id)
        
        score = score_entity.native_value
        assert score == 7.0  # 10.0 - 3.0 for fog

    def test_score_rain_penalty(self, mock_hass, score_entity):
        """Test rain reduces score."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("20"),
            "sensor.wind": MockState("10"),
            "sensor.rain": MockState("5"),  # Rain
            "weather.home": MockState("rainy"),
        }.get(entity_id)
        
        score = score_entity.native_value
        # Should be reduced due to rain (base -3.0) and possibly road state
        assert score <= 7.5 and score >= 6.0, f"Expected score between 6.0 and 7.5, got {score}"

    def test_score_cold_penalty(self, mock_hass, score_entity):
        """Test cold temperature reduces score."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("5"),  # Cold
            "sensor.wind": MockState("20"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("sunny"),
        }.get(entity_id)
        
        score = score_entity.native_value
        # Should be less than 10.0 due to windchill penalty
        assert score < 10.0

    def test_score_wind_stability_penalty(self, mock_hass, score_entity):
        """Test high wind speed affects stability."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("20"),
            "sensor.wind": MockState("50"),  # High wind
            "sensor.rain": MockState("0"),
            "weather.home": MockState("sunny"),
        }.get(entity_id)
        
        score = score_entity.native_value
        # Should be reduced due to wind stability penalty
        assert score < 10.0

    def test_score_night_mode_twilight(self, mock_hass, score_entity):
        """Test twilight reduces visibility."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("20"),
            "sensor.wind": MockState("10"),
            "sensor.rain": MockState("0"),
            "weather.home": MockState("sunny"),
            "sun.sun": MockState("at_horizon", {"elevation": 5, "azimuth": 180}),  # Twilight
        }.get(entity_id)
        
        score = score_entity.native_value
        # Should be reduced due to night mode
        assert score < 10.0

    def test_score_unavailable_sensor(self, mock_hass, score_entity):
        """Test that unavailable sensor returns None."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("unavailable"),
            "sensor.wind": MockState("10"),
            "sensor.rain": MockState("0"),
        }.get(entity_id)
        
        score = score_entity.native_value
        assert score is None

    def test_score_missing_sensor(self, mock_hass, score_entity):
        """Test that missing sensor returns None."""
        mock_hass.states.get.side_effect = lambda entity_id: None
        
        score = score_entity.native_value
        assert score is None

    def test_score_reasons_generated(self, mock_hass, score_entity):
        """Test that reasons are generated in attributes."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("20"),
            "sensor.wind": MockState("45"),  # High wind
            "sensor.rain": MockState("0"),
            "weather.home": MockState("sunny"),
            "sun.sun": MockState("above_horizon", {"elevation": 45, "azimuth": 180}),
        }.get(entity_id)
        
        score = score_entity.native_value
        reasons = score_entity._attr_extra_state_attributes.get("reasons", [])
        assert len(reasons) > 0
        assert any("Wind" in reason for reason in reasons)

    def test_score_reasons_match_score(self, mock_hass, score_entity):
        """Ensure that total malus from reasons equals the calculated malus and score is clamped correctly."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("10"),
            "sensor.wind": MockState("50"),
            "sensor.rain": MockState("2"),
            "weather.home": MockState("rainy", {"humidity": 80}),
            "sun.sun": MockState("above_horizon", {"elevation": 0, "azimuth": 180}),
        }.get(entity_id)
        
        score = score_entity.native_value
        reasons = score_entity._attr_extra_state_attributes.get("reasons", [])
        total_malus = 0.0
        for r in reasons:
            if "(" in r and ")" in r:
                try:
                    val = float(r.split("(")[-1].rstrip(")"))
                    total_malus += val
                except ValueError:
                    pass
        # Score should be clamped between 0 and 10
        expected_score = max(0, min(10, 10 + total_malus))
        assert pytest.approx(score, rel=0.01) == pytest.approx(expected_score, rel=0.01)
    @pytest.mark.parametrize("bike_type", MACHINE_TYPES)
    def test_score_all_bike_types(self, mock_hass, bike_type):
        """Test score calculation for all supported bike types."""
        from bikersentinel.sensor import BikerSentinelScore
        
        entry = MagicMock()
        entry.entry_id = "test"
        entry.data = {
            CONF_SENSOR_TEMP: "sensor.temp",
            CONF_SENSOR_WIND: "sensor.wind",
            CONF_SENSOR_RAIN: "sensor.rain",
            CONF_RIDING_CONTEXT: "road",
            CONF_RAIN_RATIO: DEFAULT_RAIN_RATIO,
            CONF_FOG_RATIO: DEFAULT_FOG_RATIO,
            CONF_CLOUDY_RATIO: DEFAULT_CLOUDY_RATIO,
            CONF_COLD_RATIO: DEFAULT_COLD_RATIO,
            CONF_HOT_RATIO: DEFAULT_HOT_RATIO,
            CONF_WIND_RATIO: DEFAULT_WIND_RATIO,
            CONF_HUMIDITY_RATIO: DEFAULT_HUMIDITY_RATIO,
            CONF_NIGHT_RATIO: DEFAULT_NIGHT_RATIO,
            CONF_ROAD_STATE_RATIO: DEFAULT_ROAD_STATE_RATIO,
        }
        entry.runtime_data = {}
        
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("20"),
            "sensor.wind": MockState("15"),
            "sensor.rain": MockState("0"),
        }.get(entity_id)
        
        score = BikerSentinelScore(mock_hass, entry, 175, 80, bike_type, "Standard", 3, "road",
                                   DEFAULT_RAIN_RATIO, DEFAULT_FOG_RATIO, DEFAULT_CLOUDY_RATIO,
                                   DEFAULT_COLD_RATIO, DEFAULT_HOT_RATIO, DEFAULT_WIND_RATIO,
                                   DEFAULT_HUMIDITY_RATIO, DEFAULT_NIGHT_RATIO, DEFAULT_ROAD_STATE_RATIO)
        result = score.native_value
        
        assert result is not None
        assert 0 <= result <= 10

    @pytest.mark.parametrize("equipment", EQUIPMENT_LEVELS)
    def test_score_all_equipment_levels(self, mock_hass, equipment):
        """Test score calculation for all equipment levels."""
        from bikersentinel.sensor import BikerSentinelScore
        
        entry = MagicMock()
        entry.entry_id = "test"
        entry.data = {
            CONF_SENSOR_TEMP: "sensor.temp",
            CONF_SENSOR_WIND: "sensor.wind",
            CONF_SENSOR_RAIN: "sensor.rain",
            CONF_RIDING_CONTEXT: "road",
            CONF_RAIN_RATIO: DEFAULT_RAIN_RATIO,
            CONF_FOG_RATIO: DEFAULT_FOG_RATIO,
            CONF_CLOUDY_RATIO: DEFAULT_CLOUDY_RATIO,
            CONF_COLD_RATIO: DEFAULT_COLD_RATIO,
            CONF_HOT_RATIO: DEFAULT_HOT_RATIO,
            CONF_WIND_RATIO: DEFAULT_WIND_RATIO,
            CONF_HUMIDITY_RATIO: DEFAULT_HUMIDITY_RATIO,
            CONF_NIGHT_RATIO: DEFAULT_NIGHT_RATIO,
            CONF_ROAD_STATE_RATIO: DEFAULT_ROAD_STATE_RATIO,
        }
        entry.runtime_data = {}
        
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp": MockState("5"),  # Cold
            "sensor.wind": MockState("20"),
            "sensor.rain": MockState("0"),
        }.get(entity_id)
        
        score = BikerSentinelScore(mock_hass, entry, 175, 80, "Roadster", equipment, 3, "road",
                                   DEFAULT_RAIN_RATIO, DEFAULT_FOG_RATIO, DEFAULT_CLOUDY_RATIO,
                                   DEFAULT_COLD_RATIO, DEFAULT_HOT_RATIO, DEFAULT_WIND_RATIO,
                                   DEFAULT_HUMIDITY_RATIO, DEFAULT_NIGHT_RATIO, DEFAULT_ROAD_STATE_RATIO)
        result = score.native_value
        
        assert result is not None
        # Heated equipment should reduce cold penalty
        if equipment == "Heated":
            assert result > 3.0  # Should have better score


class TestBikerSentinelStatus:
    """Test cases for BikerSentinelStatus entity."""
    
    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = MagicMock()
        return hass
    
    @pytest.fixture
    def mock_entry(self):
        """Create a mock config entry with runtime_data."""
        from unittest.mock import MagicMock
        entry = MagicMock()
        entry.entry_id = "test_entry_123"
        entry.data = {
            CONF_BIKE_TYPE: "Roadster",
            CONF_EQUIPMENT: "Standard",
            CONF_SENSOR_TEMP: "sensor.temp",
            CONF_SENSOR_WIND: "sensor.wind",
            CONF_SENSOR_RAIN: "sensor.rain",
            CONF_RIDING_CONTEXT: "road",
        }
        
        # Create a mock score entity
        mock_score = MagicMock()
        mock_score.native_value = 8.0
        entry.runtime_data = {"score_entity": mock_score}
        
        return entry

    @pytest.fixture
    def status_entity(self, mock_hass, mock_entry):
        """Create a BikerSentinelStatus instance."""
        from bikersentinel.sensor import BikerSentinelStatus
        return BikerSentinelStatus(mock_hass, mock_entry)

    def test_status_optimal(self, status_entity):
        """Test that high score returns 'optimal' status."""
        status_entity._entry.runtime_data["score_entity"].native_value = 8.5
        assert status_entity.native_value == "optimal"

    def test_status_favorable(self, status_entity):
        """Test that medium-high score returns 'favorable' status."""
        status_entity._entry.runtime_data["score_entity"].native_value = 6.0
        assert status_entity.native_value == "favorable"

    def test_status_degraded(self, status_entity):
        """Test that medium-low score returns 'degraded' status."""
        status_entity._entry.runtime_data["score_entity"].native_value = 4.0
        assert status_entity.native_value == "degraded"

    def test_status_critical(self, status_entity):
        """Test that low score returns 'critical' status."""
        status_entity._entry.runtime_data["score_entity"].native_value = 1.5
        assert status_entity.native_value == "critical"

    def test_status_dangerous(self, status_entity):
        """Test that zero score returns 'dangerous' status."""
        status_entity._entry.runtime_data["score_entity"].native_value = 0.0
        assert status_entity.native_value == "dangerous"


class TestBikerSentinelReasoning:
    """Test cases for BikerSentinelReasoning entity."""
    
    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        return MagicMock()
    
    @pytest.fixture
    def mock_entry(self):
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry_123"
        
        # Create a mock score entity with reasons and native_value
        mock_score = MagicMock()
        mock_score.extra_state_attributes = {
            "reasons": ["Wind 50km/h (-1.5)", "Cold Temperature (-2.0)"],
            "night_mode": "day",
        }
        mock_score.native_value = 6.5  # 10.0 - 3.5 malus
        entry.runtime_data = {"score_entity": mock_score}
        
        return entry

    @pytest.fixture
    def reasoning_entity(self, mock_hass, mock_entry):
        """Create a BikerSentinelReasoning instance."""
        from bikersentinel.sensor import BikerSentinelReasoning
        return BikerSentinelReasoning(mock_hass, mock_entry)

    def test_reasoning_primary_reason(self, reasoning_entity):
        """Test that reasons are included in output."""
        value = reasoning_entity.native_value
        # Should contain malus information
        assert "Wind" in value or "3.5" in value

    def test_reasoning_all_reasons_in_attributes(self, reasoning_entity):
        """Test that all reasons are in extra_state_attributes."""
        attrs = reasoning_entity.extra_state_attributes
        assert "all_factors" in attrs
        assert len(attrs["all_factors"]) == 2
        assert "Wind" in attrs["all_factors"][0]


class TestTripScoreEntities:
    """Test cases for Trip Score entities."""
    
    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = MagicMock()
        hass.states = MagicMock()
        return hass
    
    @pytest.fixture
    def mock_entry_with_trips(self):
        """Create a config entry with trip configuration."""
        entry = MagicMock()
        entry.entry_id = "test_entry_with_trips"
        entry.data = {
            CONF_TRIP_ENABLED: True,
            CONF_TRIP_HOME_WEATHER: "weather.morning",
            CONF_TRIP_OFFICE_WEATHER: "weather.evening",
            CONF_TRIP_DEPART_TIME: "08:00",
            CONF_TRIP_RETURN_TIME: "18:00",
        }
        # Mock score entity
        mock_score_entity = MagicMock()
        mock_score_entity.native_value = 10.0
        mock_score_entity.extra_state_attributes = {"reasons": []}
        # Initialize runtime_data with trip score entities
        entry.runtime_data = {
            "score_entity": mock_score_entity,
            "trip_score_go": None,
            "trip_score_return": None,
        }
        return entry

    @pytest.fixture
    def trip_score_go(self, mock_hass, mock_entry_with_trips):
        """Create a BikerSentinelTripScoreGo instance."""
        from bikersentinel.sensor import BikerSentinelTripScoreGo
        return BikerSentinelTripScoreGo(mock_hass, mock_entry_with_trips)

    def test_trip_score_go_initialization(self, trip_score_go):
        """Test that trip score go initializes correctly."""
        assert "trip_score_go" in trip_score_go._attr_unique_id

    def test_trip_score_go_sunny_weather(self, mock_hass, trip_score_go):
        """Test trip score with sunny weather."""
        mock_hass.states.get.return_value = MockState("sunny")
        score = trip_score_go.native_value
        assert score is not None
        assert score >= 0 and score <= 10

    def test_trip_score_go_dangerous_weather(self, mock_hass, trip_score_go):
        """Test trip score with dangerous weather."""
        mock_hass.states.get.return_value = MockState("snowy")
        score = trip_score_go.native_value
        assert score == 0.0


    @pytest.fixture
    def trip_status_go(self, mock_hass, mock_entry_with_trips):
        """Create a BikerSentinelTripStatusGo instance."""
        from bikersentinel.sensor import BikerSentinelTripStatusGo
        return BikerSentinelTripStatusGo(mock_hass, mock_entry_with_trips)

    @pytest.fixture
    def trip_status_return(self, mock_hass, mock_entry_with_trips):
        """Create a BikerSentinelTripStatusReturn instance."""
        from bikersentinel.sensor import BikerSentinelTripStatusReturn
        return BikerSentinelTripStatusReturn(mock_hass, mock_entry_with_trips)

    def test_trip_status_go_initialization(self, trip_status_go):
        """Test that trip status go initializes correctly."""
        assert "trip_status_go" in trip_status_go._attr_unique_id

    def test_trip_status_return_initialization(self, trip_status_return):
        """Test that trip status return initializes correctly."""
        assert "trip_status_return" in trip_status_return._attr_unique_id

    def test_trip_status_go_analyzing_default(self, trip_status_go):
        """Test trip status defaulting to analyzing."""
        status = trip_status_go.native_value
        # Should default to analyzing if no score entity found
        assert status in ["analyzing", "error"]

    def test_trip_status_return_analyzing_default(self, trip_status_return):
        """Test trip status defaulting to analyzing."""
        status = trip_status_return.native_value
        # Should default to analyzing if no score entity found
        assert status in ["analyzing", "error"]


class TestTripReasoningEntities:
    """Test cases for Trip Reasoning entities."""
    
    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = MagicMock()
        hass.states = MagicMock()
        return hass
    
    @pytest.fixture
    def mock_entry_with_trips(self):
        """Create a config entry with trip configuration."""
        entry = MagicMock()
        entry.entry_id = "test_entry_with_trips"
        entry.data = {
            CONF_TRIP_ENABLED: True,
            CONF_TRIP_HOME_WEATHER: "weather.office",
            CONF_TRIP_OFFICE_WEATHER: "weather.home",
            CONF_TRIP_DEPART_TIME: "08:00",
            CONF_TRIP_RETURN_TIME: "18:00",
        }
        # Mock score entity
        mock_score_entity = MagicMock()
        mock_score_entity.native_value = 10.0
        # Initialize runtime_data with trip score entities
        entry.runtime_data = {
            "score_entity": mock_score_entity,
            "trip_score_go": None,
            "trip_score_return": None,
        }
        return entry

    @pytest.fixture
    def trip_reasoning_go(self, mock_hass, mock_entry_with_trips):
        """Create a BikerSentinelTripReasoningGo instance."""
        from bikersentinel.sensor import BikerSentinelTripReasoningGo
        return BikerSentinelTripReasoningGo(mock_hass, mock_entry_with_trips)

    @pytest.fixture
    def trip_reasoning_return(self, mock_hass, mock_entry_with_trips):
        """Create a BikerSentinelTripReasoningReturn instance."""
        from bikersentinel.sensor import BikerSentinelTripReasoningReturn
        return BikerSentinelTripReasoningReturn(mock_hass, mock_entry_with_trips)

    def test_trip_reasoning_go_initialization(self, trip_reasoning_go):
        """Test that trip reasoning go initializes correctly."""
        assert "trip_reasoning_go" in trip_reasoning_go._attr_unique_id

    def test_trip_reasoning_return_initialization(self, trip_reasoning_return):
        """Test that trip reasoning return initializes correctly."""
        assert "trip_reasoning_return" in trip_reasoning_return._attr_unique_id

    def test_trip_reasoning_go_default_analyzing(self, trip_reasoning_go):
        """Test that reasoning defaults when no score found."""
        reasoning = trip_reasoning_go.native_value
        assert reasoning in ["Analyzing...", "Calculating..."]

    def test_trip_reasoning_return_default_analyzing(self, trip_reasoning_return):
        """Test that reasoning defaults when no score found."""
        reasoning = trip_reasoning_return.native_value
        assert reasoning in ["Analyzing...", "Calculating..."]

    def test_trip_reasoning_go_matches_score_drop(self, mock_hass, mock_entry_with_trips, trip_reasoning_go):
        """Test that trip reasoning total matches score drop from 10.0."""
        # Mock trip score entity
        mock_trip_score = MagicMock()
        mock_trip_score.native_value = 7.0
        mock_trip_score.extra_state_attributes = {
            "reasons": ["Home: Rain (-1.5)", "Home: Humidity 90.0% (-0.5)", "Office: Cold 6.4°C (-1.0)"]
        }
        mock_entry_with_trips.runtime_data["trip_score_go"] = mock_trip_score
        
        reasoning = trip_reasoning_go.native_value
        # Should show -3.0 (10.0 - 7.0)
        assert "-3.0" in reasoning

    def test_trip_reasoning_return_matches_score_drop(self, mock_hass, mock_entry_with_trips, trip_reasoning_return):
        """Test that trip reasoning total matches score drop from 10.0."""
        # Mock trip score entity
        mock_trip_score = MagicMock()
        mock_trip_score.native_value = 7.0
        mock_trip_score.extra_state_attributes = {
            "reasons": ["Office: Rain (-1.5)", "Home: Humidity 90.0% (-0.5)", "Home: Cold 6.4°C (-1.0)"]
        }
        mock_entry_with_trips.runtime_data["trip_score_return"] = mock_trip_score
        
        reasoning = trip_reasoning_return.native_value
        # Should show -3.0 (10.0 - 7.0)
        assert "-3.0" in reasoning



