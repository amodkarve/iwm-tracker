# Fuzzy Logic Unit Tests

This directory contains comprehensive unit tests for the fuzzy logic trading strategy system.

## Test Files

### `test_fuzzy_engine.py`
Tests the core fuzzy logic engine:
- `FuzzySet`: Membership function calculations (triangular and trapezoidal)
- `FuzzyVar`: Fuzzification of crisp inputs
- Fuzzy operations: AND, OR, NOT
- Defuzzification: Centroid method

### `test_fuzzy_strategy.py`
Tests all fuzzy rule functions based on original requirements:
- **Put Moneyness Rules**:
  - Oversold & trend up → ITM (-1 to -2)
  - Oversold & trend down → ATM
  - Overbought & trend up → slightly OTM (+1)
  - Overbought & trend down → more OTM (+2)
  
- **Put Size Fraction Rules**:
  - Premium gap far below → large size (~1.0)
  - Premium gap slightly below → medium size (~0.5)
  - Premium gap met → small size (~0.2)
  - Critical BP reduces size
  - High VIX allows more aggressive sizing

- **Call Sell Score Rules**:
  - Deep loss & below BE → high risk (low score)
  - Profit & above BE → low risk (high score)
  - High IV & high premium → attractive (high score)
  - Low IV & low premium → unattractive (low score)

- **Call Moneyness Rules**:
  - Trend up & cycle oversold → further OTM (+3)
  - Trend down & cycle overbought → closer to BE (+0.5)

- **Convert Score Rules**:
  - Critical BP & heavy stock → high conversion
  - Tight BP & heavy stock → medium conversion
  - Comfortable BP or light stock → low conversion
  - High VIX → shallow ITM depth (delta 0.7)
  - Low VIX → deep ITM depth (delta 0.9)

- **Hedge Score Rules**:
  - Low VIX & overbought & trend up → high hedge
  - Mid VIX & heavy stock → medium hedge
  - High VIX & not overbought → low hedge (expensive)
  - Low VIX → larger OTM distance (10-15%)
  - High VIX → smaller OTM distance (5-8%)

### `test_fuzzy_inputs.py`
Tests input calculation functions:
- VIX normalization (with and without history)
- Trend normalization from Ehlers indicator
- Cycle normalization from Cycle Swing indicator
- Portfolio metrics calculation (BP fraction, stock weight, premium gap)
- Assigned share metrics (unrealized PnL, days since assignment)

### `test_fuzzy_recommendations.py`
Tests the fuzzy recommendation engine:
- Put recommendations generation
- Call recommendations generation
- Hedge recommendations generation
- Edge cases (no options, no shares, low scores)

## Running Tests

Run all fuzzy logic tests:
```bash
pytest tests/unit/test_fuzzy_*.py -v
```

Run specific test file:
```bash
pytest tests/unit/test_fuzzy_engine.py -v
pytest tests/unit/test_fuzzy_strategy.py -v
pytest tests/unit/test_fuzzy_inputs.py -v
pytest tests/unit/test_fuzzy_recommendations.py -v
```

Run in Docker (as per project setup):
```bash
docker-compose -f docker-compose.test.yml run --rm backend pytest tests/unit/test_fuzzy_*.py -v
```

## Test Philosophy

These tests are based on the **original requirements** provided in the user's specification. The tests define the expected behavior, and the implementation was adjusted to match the test expectations (not vice versa).

Key principles:
1. Tests verify fuzzy membership functions work correctly
2. Tests verify rule outputs match expected ranges
3. Tests verify edge cases are handled gracefully
4. Tests use mocking to isolate units under test

## Coverage

The tests cover:
- ✅ All fuzzy set operations
- ✅ All fuzzy rule functions
- ✅ All input calculation functions
- ✅ All recommendation generation functions
- ✅ Edge cases and error handling
- ✅ Range validation (all outputs in expected ranges)

