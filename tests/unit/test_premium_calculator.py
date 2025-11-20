"""
Unit tests for premium calculator
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.strategy.premium_calculator import (
    calculate_daily_target,
    calculate_contracts_needed,
    calculate_expected_premium,
    calculate_premium_percentage,
    get_position_sizing_recommendation
)


def test_calculate_daily_target():
    """Test daily premium target calculation"""
    # Test with $1M account and 0.08% target
    target = calculate_daily_target(1_000_000, 0.0008)
    assert target == 800.0, f"Expected 800.0, got {target}"
    
    # Test with smaller account
    target = calculate_daily_target(500_000, 0.0008)
    assert target == 600.0, f"Expected 600.0 (min), got {target}"  # Should hit minimum
    
    print("✓ test_calculate_daily_target passed")


def test_calculate_contracts_needed():
    """Test contract sizing calculation"""
    # $80 per contract, $800 target = 10 contracts
    contracts = calculate_contracts_needed(80, 800)
    assert contracts == 10, f"Expected 10, got {contracts}"
    
    # $100 per contract, $800 target = 8 contracts
    contracts = calculate_contracts_needed(100, 800)
    assert contracts == 8, f"Expected 8, got {contracts}"
    
    # Very high premium - should cap at MAX_CONTRACTS (10)
    contracts = calculate_contracts_needed(50, 800)
    assert contracts == 10, f"Expected 10 (max), got {contracts}"
    
    # Very low premium - should use MIN_CONTRACTS (5)
    contracts = calculate_contracts_needed(10, 800)
    assert contracts == 10, f"Expected 10, got {contracts}"
    
    print("✓ test_calculate_contracts_needed passed")


def test_calculate_expected_premium():
    """Test expected premium calculation"""
    # $0.80 per share * 10 contracts * 100 shares = $800
    premium = calculate_expected_premium(0.80, 10)
    assert premium == 800.0, f"Expected 800.0, got {premium}"
    
    # $1.50 per share * 5 contracts * 100 shares = $750
    premium = calculate_expected_premium(1.50, 5)
    assert premium == 750.0, f"Expected 750.0, got {premium}"
    
    print("✓ test_calculate_expected_premium passed")


def test_calculate_premium_percentage():
    """Test premium percentage calculation"""
    # $800 premium on $1M account = 0.0008 (0.08%)
    pct = calculate_premium_percentage(800, 1_000_000)
    assert abs(pct - 0.0008) < 0.0001, f"Expected 0.0008, got {pct}"
    
    # $400 premium on $500k account = 0.0008 (0.08%)
    pct = calculate_premium_percentage(400, 500_000)
    assert abs(pct - 0.0008) < 0.0001, f"Expected 0.0008, got {pct}"
    
    print("✓ test_calculate_premium_percentage passed")


def test_get_position_sizing_recommendation():
    """Test complete position sizing recommendation"""
    rec = get_position_sizing_recommendation(0.80, 1_000_000)
    
    assert rec['target_premium'] == 800.0, f"Expected target 800.0, got {rec['target_premium']}"
    assert rec['contracts'] == 10, f"Expected 10 contracts, got {rec['contracts']}"
    assert rec['expected_premium'] == 800.0, f"Expected premium 800.0, got {rec['expected_premium']}"
    assert abs(rec['premium_pct'] - 0.0008) < 0.0001, f"Expected 0.0008%, got {rec['premium_pct']}"
    
    print("✓ test_get_position_sizing_recommendation passed")


if __name__ == "__main__":
    test_calculate_daily_target()
    test_calculate_contracts_needed()
    test_calculate_expected_premium()
    test_calculate_premium_percentage()
    test_get_position_sizing_recommendation()
    
    print("\n✅ All premium calculator tests passed!")
