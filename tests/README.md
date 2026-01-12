# Tests for BikerSentinel

## Running tests

```bash
# Installation of dependencies
pip install pytest pytest-asyncio homeassistant

# Run all tests
pytest tests/ -v

# Run a specific test
pytest tests/test_algorithm.py::TestBikerSentinelScore::test_perfect_conditions_score_10 -v

# With code coverage
pip install pytest-cov
pytest tests/ --cov=bikersentinel --cov-report=html
```

## Test structure

### `test_algorithm.py`

**Test classes:**
- `TestBikerSentinelScore` : 30+ tests for the score algorithm
- `TestBikerSentinelStatus` : 10+ tests for status mapping

**Coverage:**

1. **Security Vetoes (5 tests)**
   - Ice risk (T < 1°C) → 0
   - Storm winds (V > 85 km/h) → 0
   - Dangerous weather (Snow, Hail, Storm) → 0

2. **Nominal Conditions (2 tests)**
   - Perfect conditions → 10
   - Good conditions → high score

3. **Wind Chill (2 tests)**
   - Cold temp produces penalty
   - Above 15°C threshold: no cold penalty

4. **Equipment (3 tests)**
   - Heated (0.3x) > Winter (0.6x) > Standard (1.0x)
   - Verify progressive cold penalty reduction

5. **Cold Sensitivity (3 tests)**
   - Viking (1) : reduces cold penalty (0.8x)
   - Normal (3) : no modification (1.0x)
   - Sensitive (5) : increases cold penalty (1.2x)

6. **Wind & Stability (2 tests)**
   - Wind > 35 km/h → progressive penalty
   - Wind ≤ 35 km/h → no wind penalty

7. **Rain (2 tests)**
   - Rain > 0 mm → -3 penalty
   - No rain → 0 penalty

8. **Fog (1 test)**
   - Fog → -3 penalty

9. **Motorcycle Coefficients (2 tests)**
   - GT (0.7) > Roadster (1.2) → better protection
   - Verify impact on cold and wind penalties

10. **Edge Cases (3 tests)**
    - Min score ≥ 0
    - Max score ≤ 10
    - Unavailable sensors → None

11. **Status Mapping (10 parameterized tests)**
    - 9.0 → optimal
    - 7.0 → favorable
    - 5.0 → degraded
    - 3.0 → critical
    - < 3.0 → dangerous

## Execution example

```
============================= test_algorithm.py ==============================
test_algorithm.py::TestBikerSentinelScore::test_perfect_conditions_score_10 PASSED
test_algorithm.py::TestBikerSentinelScore::test_veto_ice_risk_temp_below_1 PASSED
test_algorithm.py::TestBikerSentinelScore::test_windchill_cold_temp_malus PASSED
test_algorithm.py::TestBikerSentinelScore::test_equipment_heated_reduces_cold_malus PASSED
...
========================== 40+ tests passed in 0.23s ==========================
```

## Expected results

✅ All security vetoes block the score
✅ Score increases/decreases with conditions
✅ Equipment progressively reduces cold
✅ Cold sensitivity amplifies/reduces cold
✅ Wind generates penalty > 35 km/h
✅ Rain and fog apply -3 penalty
✅ Motorcycle types change protection
✅ Score always between 0 and 10
✅ Unavailable sensors return None
✅ Status correctly maps score ranges
