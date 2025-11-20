"""
Premium Calculator

Calculates premium targets and position sizing based on account size
and strategy rules.
"""
from typing import Dict
from .rules import (
    TARGET_DAILY_PREMIUM_PCT,
    TARGET_DAILY_PREMIUM_MIN,
    TARGET_DAILY_PREMIUM_MAX,
    MIN_CONTRACTS,
    MAX_CONTRACTS,
    CONTRACTS_PER_100_SHARES,
    DEFAULT_ACCOUNT_SIZE
)


def calculate_daily_target(
    account_value: float = DEFAULT_ACCOUNT_SIZE,
    target_pct: float = TARGET_DAILY_PREMIUM_PCT
) -> float:
    """
    Calculate daily premium target based on account value
    
    Args:
        account_value: Total account value
        target_pct: Target daily premium as percentage (default 0.08%)
    
    Returns:
        Daily premium target in dollars
    
    Example:
        >>> calculate_daily_target(1_000_000, 0.0008)
        800.0
    """
    target = account_value * target_pct
    
    # Ensure within min/max bounds
    return max(TARGET_DAILY_PREMIUM_MIN, min(target, TARGET_DAILY_PREMIUM_MAX))


def calculate_contracts_needed(
    premium_per_contract: float,
    target_premium: float
) -> int:
    """
    Calculate number of contracts needed to reach target premium
    
    Args:
        premium_per_contract: Premium per contract in dollars (price * 100)
        target_premium: Target total premium in dollars
    
    Returns:
        Number of contracts (constrained by MIN/MAX_CONTRACTS)
    
    Example:
        >>> calculate_contracts_needed(80, 800)  # $0.80 per share = $80 per contract
        10
    """
    if premium_per_contract <= 0:
        return MIN_CONTRACTS
    
    contracts = int(target_premium / premium_per_contract)
    
    # Constrain to min/max
    return max(MIN_CONTRACTS, min(contracts, MAX_CONTRACTS))


def calculate_expected_premium(
    option_price: float,
    contracts: int
) -> float:
    """
    Calculate expected premium for a trade
    
    Args:
        option_price: Option price per share (e.g., 0.80)
        contracts: Number of contracts
    
    Returns:
        Total premium in dollars
    
    Example:
        >>> calculate_expected_premium(0.80, 10)
        800.0
    """
    return option_price * contracts * 100  # 100 shares per contract


def calculate_premium_percentage(
    premium: float,
    account_value: float = DEFAULT_ACCOUNT_SIZE
) -> float:
    """
    Calculate premium as percentage of account value
    
    Args:
        premium: Premium amount in dollars
        account_value: Total account value
    
    Returns:
        Premium as percentage (e.g., 0.0008 for 0.08%)
    
    Example:
        >>> calculate_premium_percentage(800, 1_000_000)
        0.0008
    """
    if account_value <= 0:
        return 0.0
    
    return premium / account_value


def get_position_sizing_recommendation(
    option_price: float,
    account_value: float = DEFAULT_ACCOUNT_SIZE,
    target_pct: float = TARGET_DAILY_PREMIUM_PCT
) -> Dict[str, float]:
    """
    Get complete position sizing recommendation
    
    Args:
        option_price: Option price per share
        account_value: Total account value
        target_pct: Target daily premium percentage
    
    Returns:
        Dictionary with:
        - target_premium: Daily premium target
        - contracts: Recommended number of contracts
        - expected_premium: Expected premium from recommendation
        - premium_pct: Expected premium as percentage
    
    Example:
        >>> get_position_sizing_recommendation(0.80, 1_000_000)
        {
            'target_premium': 800.0,
            'contracts': 10,
            'expected_premium': 800.0,
            'premium_pct': 0.0008
        }
    """
    target_premium = calculate_daily_target(account_value, target_pct)
    premium_per_contract = option_price * 100
    contracts = calculate_contracts_needed(premium_per_contract, target_premium)
    expected_premium = calculate_expected_premium(option_price, contracts)
    premium_pct = calculate_premium_percentage(expected_premium, account_value)
    
    return {
        'target_premium': target_premium,
        'contracts': contracts,
        'expected_premium': expected_premium,
        'premium_pct': premium_pct
    }
