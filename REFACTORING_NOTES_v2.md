# BikerSentinel v2.0.0 - UX Redesign Refactoring

## Summary

Complete refactoring of BikerSentinel v2.0.0 based on user feedback from actual Home Assistant testing. The integration was technically working (74/74 tests passing) but had poor UX with too many configuration options and exposed entities, making it confusing for typical users.

## Changes Made

### 1. Configuration Flow (`config_flow.py`) - REFACTORED
**Before:** Single dense screen with 15+ fields and 6 mysterious toggles
**After:** Multi-step, clean configuration with 3 logical sections:

- **Step 1 "user"**: Weather Sensors + Rider Profile (Required)
  - Section 1: Temperature, Wind, Rain sensors (mandatory)
  - Section 2: Height, Weight, Bike Type, Equipment, Riding Context, Sensitivity, Weather Entity (required profile)
  - Option: Enable Trip Forecasting

- **Step 2 "trips"**: Trip Configuration (Optional, only if enabled)
  - Outbound journey: Weather source + departure time
  - Return journey: Weather source + return time

### 2. Constants (`const.py`) - SIMPLIFIED
Removed all feature toggle constants (these features are now always-on internally):
- ❌ `CONF_NIGHT_MODE_ENABLED` → Feature always active
- ❌ `CONF_PRECIP_HISTORY_ENABLED` → Feature always active
- ❌ `CONF_TEMP_HUMIDITY_TRENDS_ENABLED` → Feature always active
- ❌ `CONF_SOLAR_BLINDNESS_ENABLED` → Feature always active
- ❌ `CONF_COMMUTE_ALERT_ENABLED` → Removed (potential Home Assistant automation)
- ✅ **Kept**: `CONF_TRIP_ENABLED` (legitimately optional for users who don't commute)

### 3. Sensor Entities (`sensor.py`) - DRASTICALLY REFACTORED
**Before:** 10 exposed sensor entities (confusing, noisy)
```
- BikerSentinelScore
- BikerSentinelStatus
- BikerSentinelReasoning
- BikerSentinelNightMode ❌ REMOVED
- BikerSentinelPrecipitationHistory ❌ REMOVED
- BikerSentinelTripScore ❌ SPLIT INTO 2
- BikerSentinelTemperatureTrend ❌ REMOVED
- BikerSentinelHumidityTrend ❌ REMOVED
- BikerSentinelSolarBlindness ❌ REMOVED
- BikerSentinelCommuteAlert ❌ REMOVED
```

**After:** Only 4-5 essential entities exposed
```
✅ BikerSentinelScore (0-10 numeric rating)
✅ BikerSentinelStatus (Optimal/Favorable/Degraded/Critical/Dangerous)
✅ BikerSentinelReasoning (Explanation of score)
✅ BikerSentinelTripScoreGo (If trips enabled - outbound journey score)
✅ BikerSentinelTripScoreReturn (If trips enabled - return journey score)
```

**Internal Features (Hidden):**
- Night Mode: Always active, calculated internally, reflected in Score via visibility malus
- Precipitation History: 24h tracking for road state correlation, internal calculation
- Temperature Trends: Icing risk detection, included in reasoning
- Humidity: Visibility impact calculation, internal processing
- Solar Blindness: Sun glare detection, included in Score malus
- Commute Alert: Could be implemented as Home Assistant automation

### 4. Enhanced Score Calculation
The `BikerSentinelScore.native_value` now includes ALL advanced features internally:

1. **Safety Vetoes** (Immediate 0.0)
   - Dangerous weather (snowy, hail, lightning-rainy)
   - Ice risk (temp < 1°C)
   - Storm winds (> 85 km/h)

2. **Visibility Factors**
   - Fog (-3.0)
   - Night Mode: Solar elevation-based malus (-1.5 to -5.0)

3. **Solar Blindness** (Glare Detection)
   - Safe: 0.0
   - Caution: -1.0 (sun approaching front)
   - Warning: -2.5 (sun at prime glare angle)

4. **Windchill** (Thermal Comfort - Core)
   - Dynamic calculation based on riding context
   - Equipment factor (Standard/Winter/Heated)
   - Sensitivity factor (Viking/Normal/Sensitive)

5. **Wind Stability** (Lateral Forces)
   - Penalty for winds > 35 km/h

6. **Rain/Road State** (24h Precipitation History)
   - Dry: 0.0
   - Damp: -1.0
   - Wet: -3.0
   - Sludge: -6.0
   - Icy (temp < 0): -8.0

7. **Temperature Trends** (Icing Risk)
   - Dropping rapidly: -2.0
   - Rising: +0.5
   - Stable: 0.0

8. **Humidity Impact** (Visibility/Fog)
   - High (>70%): -1.5

### 5. Reasoning Entity Enhanced
`BikerSentinelReasoning` now includes detailed attributes:
- `reasons`: List of factors affecting score
- `night_mode`: Current visibility status (day/twilight/civil_twilight/night)
- `road_state`: Inferred surface condition (dry/damp/wet/sludge/icy/unknown)
- `temperature_trend`: Direction of temperature change
- `humidity`: Visibility level
- `solar_glare`: Sun glare risk status (safe/caution/warning)

### 6. Test Suite (`tests/test_algorithm.py`) - REFACTORED
**Before:** 847 lines with many deprecated features
**After:** 439 lines, focused on core functionality:
- ✅ 32 tests passing
- Covers: Score calculation, Status mapping, Reasoning, Trip scores, All bike types, All equipment levels

### 7. Translations Updated (`en.json`, `fr.json`)
- Updated config flow step descriptions  
- Added Trip Score entity names
- Clearer field descriptions (now 3 sections instead of flat list)

## Benefits

### For Users
1. **Simpler Configuration**: 3 logical steps instead of overwhelming single form
2. **Cleaner Dashboard**: Only 4-5 entities shown (not 10 confusing ones)
3. **Clear Explanation**: Reasoning sensor explains what's affecting the score
4. **Always-On Features**: No need to toggle Night Mode, Precipitation, Trends, Solar Blindness - they just work
5. **Optional Features**: Only enable Trip Forecasting if you need it

### For Code Quality
1. **Consolidated Logic**: All calculations in one Score entity (easier to maintain)
2. **Reduced Complexity**: 60% fewer exposed entities
3. **Better Defaults**: Features are sensible by default
4. **Cleaner Architecture**: Runtime data pattern working well

## Migration Path

Users upgrading from v2.0beta → v2.0.0:
- Old entities will no longer appear (Night Mode, Precip History, Trends, Solar, Commute Alert)
- Their functionality is integrated into Score/Reasoning
- Trip Score entities may appear if trips were configured
- Manual entity cleanup recommended (remove old sensors from automations/dashboards)

## Manifest Version

- **Version**: 2.0.0 (unchanged during refactor - it's a UX improvement to existing 2.0.0 feature set)
- Status: Ready for production testing by user

## Next Steps

1. User tests on actual Home Assistant instance
2. Verify all 5 entities appear correctly
3. Test automations using Score/Status
4. Confirm no missing functionality
5. Merge to main and tag as stable v2.0.0
