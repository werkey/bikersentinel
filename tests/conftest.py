"""Pytest configuration for BikerSentinel tests."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add bikersentinel module to path
bikersentinel_path = Path(__file__).parent.parent
sys.path.insert(0, str(bikersentinel_path))

# Create comprehensive mocks for Home Assistant - MUST be done before any imports
def create_ha_mocks():
    """Create all necessary Home Assistant module mocks."""
    
    # Base modules
    ha_mock = MagicMock()
    sys.modules['homeassistant'] = ha_mock
    
    # homeassistant.core
    core_mock = MagicMock()
    sys.modules['homeassistant.core'] = core_mock
    core_mock.HomeAssistant = MagicMock
    
    # homeassistant.const
    const_mock = MagicMock()
    sys.modules['homeassistant.const'] = const_mock
    const_mock.Platform = MagicMock()
    const_mock.Platform.SENSOR = "sensor"
    
    # homeassistant.config_entries
    config_entries_mock = MagicMock()
    sys.modules['homeassistant.config_entries'] = config_entries_mock
    config_entries_mock.ConfigEntry = MagicMock
    config_entries_mock.ConfigFlow = MagicMock
    
    # homeassistant.helpers
    helpers_mock = MagicMock()
    sys.modules['homeassistant.helpers'] = helpers_mock
    
    # homeassistant.helpers.entity_platform
    entity_platform_mock = MagicMock()
    sys.modules['homeassistant.helpers.entity_platform'] = entity_platform_mock
    entity_platform_mock.AddEntitiesCallback = MagicMock
    
    # homeassistant.helpers.entity_registry
    entity_registry_mock = MagicMock()
    sys.modules['homeassistant.helpers.entity_registry'] = entity_registry_mock
    entity_registry_mock.async_get = MagicMock()
    
    # homeassistant.helpers.selector
    selector_mock = MagicMock()
    sys.modules['homeassistant.helpers.selector'] = selector_mock
    selector_mock.EntitySelector = MagicMock
    selector_mock.EntitySelectorConfig = MagicMock
    
    # homeassistant.data_entry_flow
    data_entry_flow_mock = MagicMock()
    sys.modules['homeassistant.data_entry_flow'] = data_entry_flow_mock
    data_entry_flow_mock.FlowResult = dict
    
    # homeassistant.components
    components_mock = MagicMock()
    sys.modules['homeassistant.components'] = components_mock
    
    # homeassistant.components.sensor
    sensor_mock = MagicMock()
    sys.modules['homeassistant.components.sensor'] = sensor_mock
    
    class MockSensorEntity:
        _attr_has_entity_name = None
        _attr_translation_key = None
        _attr_native_unit_of_measurement = None
        _attr_icon = None
        _attr_state_class = None
        _attr_unique_id = None
        _attr_extra_state_attributes = None
        _attr_device_class = None
        _attr_options = None
        @property
        def native_value(self):
            return None
    
    sensor_mock.SensorEntity = MockSensorEntity
    sensor_mock.SensorDeviceClass = MagicMock()
    sensor_mock.SensorStateClass = MagicMock()
    sensor_mock.SensorStateClass.MEASUREMENT = "measurement"

# Must be called BEFORE importing bikersentinel modules
create_ha_mocks()

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
