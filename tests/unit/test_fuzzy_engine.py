"""
Unit tests for fuzzy logic engine

Tests FuzzySet, FuzzyVar, and defuzzification functions
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from src.strategy.fuzzy_engine import (
    FuzzySet,
    FuzzyVar,
    defuzzify_centroid,
    fuzzy_and,
    fuzzy_or,
    fuzzy_not
)


class TestFuzzySet:
    """Test FuzzySet membership functions"""
    
    def test_triangular_membership_peak(self):
        """Test triangular membership at peak"""
        fs = FuzzySet("test", 0.0, 1.0, 2.0)
        assert fs.mu(1.0) == 1.0, "Peak should have membership 1.0"
        assert fs.mu(1.5) == 1.0, "Between b and c should have membership 1.0"
    
    def test_triangular_membership_rising_edge(self):
        """Test triangular membership on rising edge"""
        fs = FuzzySet("test", 0.0, 1.0, 2.0)
        assert fs.mu(0.0) == 0.0, "Left edge should have membership 0.0"
        assert abs(fs.mu(0.5) - 0.5) < 0.001, "Midpoint of rising edge should be 0.5"
    
    def test_triangular_membership_falling_edge(self):
        """Test triangular membership on falling edge"""
        fs = FuzzySet("test", 0.0, 1.0, 2.0)
        assert fs.mu(2.0) == 0.0, "Right edge should have membership 0.0"
        assert abs(fs.mu(1.75) - 0.5) < 0.001, "Midpoint of falling edge should be 0.5"
    
    def test_triangular_membership_outside(self):
        """Test triangular membership outside range"""
        fs = FuzzySet("test", 0.0, 1.0, 2.0)
        assert fs.mu(-1.0) == 0.0, "Left of range should be 0.0"
        assert fs.mu(3.0) == 0.0, "Right of range should be 0.0"
    
    def test_trapezoidal_membership_flat_top(self):
        """Test trapezoidal membership on flat top"""
        fs = FuzzySet("test", 0.0, 1.0, 2.0, 3.0)
        assert fs.mu(1.0) == 1.0, "Start of flat top should be 1.0"
        assert fs.mu(1.5) == 1.0, "Middle of flat top should be 1.0"
        assert fs.mu(2.0) == 1.0, "End of flat top should be 1.0"
    
    def test_trapezoidal_membership_edges(self):
        """Test trapezoidal membership on edges"""
        fs = FuzzySet("test", 0.0, 1.0, 2.0, 3.0)
        assert fs.mu(0.0) == 0.0, "Left edge should be 0.0"
        assert fs.mu(3.0) == 0.0, "Right edge should be 0.0"
        assert abs(fs.mu(0.5) - 0.5) < 0.001, "Rising edge midpoint should be 0.5"
        assert abs(fs.mu(2.5) - 0.5) < 0.001, "Falling edge midpoint should be 0.5"


class TestFuzzyVar:
    """Test FuzzyVar fuzzification"""
    
    def test_fuzzify_single_set(self):
        """Test fuzzification with single set"""
        fs = FuzzySet("low", 0.0, 0.0, 0.5, 1.0)
        fv = FuzzyVar("test", [fs])
        
        result = fv.fuzzify(0.25)
        assert "low" in result
        assert result["low"] > 0.0, "Should have some membership"
    
    def test_fuzzify_multiple_sets(self):
        """Test fuzzification with multiple overlapping sets"""
        sets = [
            FuzzySet("low", 0.0, 0.0, 0.3, 0.5),
            FuzzySet("mid", 0.3, 0.5, 0.7, 0.9),
            FuzzySet("high", 0.7, 0.9, 1.0, 1.0)
        ]
        fv = FuzzyVar("test", sets)
        
        result = fv.fuzzify(0.4)
        assert "low" in result
        assert "mid" in result
        assert "high" in result
        assert result["mid"] > result["low"], "Should have higher membership in mid"
        assert result["high"] == 0.0, "Should have no membership in high"
    
    def test_fuzzify_boundary(self):
        """Test fuzzification at set boundaries"""
        sets = [
            FuzzySet("low", 0.0, 0.0, 0.5, 1.0),
            FuzzySet("high", 0.5, 1.0, 1.0, 1.0)
        ]
        fv = FuzzyVar("test", sets)
        
        result = fv.fuzzify(0.5)
        assert result["low"] > 0.0 or result["high"] > 0.0, "Should have membership in at least one set"


class TestFuzzyOperations:
    """Test fuzzy logic operations"""
    
    def test_fuzzy_and(self):
        """Test fuzzy AND (minimum)"""
        assert fuzzy_and(0.3, 0.7) == 0.3, "AND should return minimum"
        assert fuzzy_and(0.8, 0.2, 0.5) == 0.2, "AND should return minimum of all"
        assert fuzzy_and(1.0, 1.0) == 1.0, "AND of 1.0 and 1.0 should be 1.0"
        assert fuzzy_and(0.0, 0.5) == 0.0, "AND with 0.0 should be 0.0"
    
    def test_fuzzy_or(self):
        """Test fuzzy OR (maximum)"""
        assert fuzzy_or(0.3, 0.7) == 0.7, "OR should return maximum"
        assert fuzzy_or(0.2, 0.8, 0.5) == 0.8, "OR should return maximum of all"
        assert fuzzy_or(0.0, 0.0) == 0.0, "OR of 0.0 and 0.0 should be 0.0"
        assert fuzzy_or(1.0, 0.5) == 1.0, "OR with 1.0 should be 1.0"
    
    def test_fuzzy_not(self):
        """Test fuzzy NOT (complement)"""
        assert fuzzy_not(0.0) == 1.0, "NOT of 0.0 should be 1.0"
        assert fuzzy_not(1.0) == 0.0, "NOT of 1.0 should be 0.0"
        assert abs(fuzzy_not(0.5) - 0.5) < 0.001, "NOT of 0.5 should be 0.5"


class TestDefuzzification:
    """Test defuzzification functions"""
    
    def test_defuzzify_centroid_single(self):
        """Test centroid defuzzification with single value"""
        weights = {"high": 1.0}
        values = {"high": 5.0}
        result = defuzzify_centroid(weights, values)
        assert result == 5.0, "Single value should return that value"
    
    def test_defuzzify_centroid_weighted_average(self):
        """Test centroid defuzzification with weighted average"""
        weights = {"low": 0.3, "high": 0.7}
        values = {"low": 1.0, "high": 5.0}
        result = defuzzify_centroid(weights, values)
        expected = (0.3 * 1.0 + 0.7 * 5.0) / (0.3 + 0.7)
        assert abs(result - expected) < 0.001, f"Should be weighted average: {expected}"
    
    def test_defuzzify_centroid_empty(self):
        """Test centroid defuzzification with empty inputs"""
        result = defuzzify_centroid({}, {})
        assert result == 0.0, "Empty inputs should return 0.0"
    
    def test_defuzzify_centroid_zero_weights(self):
        """Test centroid defuzzification with zero weights"""
        weights = {"low": 0.0, "high": 0.0}
        values = {"low": 1.0, "high": 5.0}
        result = defuzzify_centroid(weights, values)
        assert result == 0.0, "Zero weights should return 0.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

