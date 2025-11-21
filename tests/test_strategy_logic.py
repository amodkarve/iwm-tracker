import pytest
from datetime import datetime, date, timedelta
from src.wheeltracker.models import Trade
from src.strategy.position_manager import calculate_capital_usage, get_current_positions
from src.strategy.trade_recommendations import get_hedging_recommendation, get_stock_replacement_recommendation

@pytest.fixture
def sample_trades():
    return [
        # Long Stock: 100 shares of IWM at $200
        Trade(
            symbol="IWM",
            quantity=100,
            price=200.0,
            side="buy",
            timestamp=datetime.now(),
            option_type="stock"
        ),
        # Short Put: 1 contract of IWM 190P (Cash Secured)
        Trade(
            symbol="IWM",
            quantity=1,
            price=1.50,
            side="sell",
            timestamp=datetime.now(),
            option_type="put",
            strike_price=190.0,
            expiration_date=datetime.now() + timedelta(days=30)
        )
    ]

def test_calculate_capital_usage(sample_trades):
    # Account Value: $100,000
    # IWM Price: $205
    
    # Expected Capital:
    # Stock: 100 shares * $205 = $20,500
    # Put: 1 contract * 100 * $190 Strike = $19,000
    # Total: $39,500
    
    stats = calculate_capital_usage(
        sample_trades, 
        account_value=100000.0, 
        current_prices={'IWM': 205.0}
    )
    
    assert stats['long_stock'] == 20500.0
    assert stats['cash_secured_puts'] == 19000.0
    assert stats['total_deployed'] == 39500.0
    assert stats['buying_power_usage_pct'] == 0.395
    assert stats['stock_positions']['IWM'] == 100

def test_hedging_trigger():
    # Trigger: Bearish Trend (-1) AND Bearish Momentum (-1)
    # Portfolio: 200 shares IWM (Long)
    
    positions = {'stock': {'IWM': 200}}
    
    rec = get_hedging_recommendation(
        account_value=100000.0,
        current_positions=positions,
        trend_signal=-1,
        momentum_signal=-1,
        iwm_price=200.0
    )
    
    assert rec is not None
    assert rec.option_type == 'put'
    assert "HEDGE" in rec.reason
    assert rec.recommended_contracts == 1 # 1 put per 200 shares

def test_hedging_no_trigger():
    # No Trigger: Bullish Trend (1)
    positions = {'stock': {'IWM': 200}}
    
    rec = get_hedging_recommendation(
        account_value=100000.0,
        current_positions=positions,
        trend_signal=1,
        momentum_signal=-1,
        iwm_price=200.0
    )
    
    assert rec is None

def test_stock_replacement_trigger_efficiency():
    # Trigger: Bullish Trend (1) AND High Capital Usage (>75%)
    
    capital_stats = {
        'buying_power_usage_pct': 0.80,
        'stock_positions': {'IWM': 100}
    }
    
    rec = get_stock_replacement_recommendation(
        account_value=100000.0,
        capital_usage=capital_stats,
        trend_signal=1,
        iwm_price=200.0
    )
    
    assert rec is not None
    assert "EFFICIENCY" in rec.reason
    assert rec.confidence == "medium"

def test_stock_replacement_trigger_critical():
    # Trigger: Bearish Trend (-1) BUT Critical Capital Usage (>90%)
    # Should trigger because we need to free up BP
    
    capital_stats = {
        'buying_power_usage_pct': 0.95,
        'stock_positions': {'IWM': 100}
    }
    
    rec = get_stock_replacement_recommendation(
        account_value=100000.0,
        capital_usage=capital_stats,
        trend_signal=-1, # Bearish
        iwm_price=200.0
    )
    
    assert rec is not None
    assert "CRITICAL BP" in rec.reason
    assert rec.confidence == "high"

def test_stock_replacement_no_trigger_bearish_high():
    # No Trigger: Bearish Trend (-1) AND High Usage (80%)
    # Not critical enough to force replacement in a downtrend
    
    capital_stats = {
        'buying_power_usage_pct': 0.80,
        'stock_positions': {'IWM': 100}
    }
    
    rec = get_stock_replacement_recommendation(
        account_value=100000.0,
        capital_usage=capital_stats,
        trend_signal=-1,
        iwm_price=200.0
    )
    
    assert rec is None

def test_calculate_capital_usage_covered_call():
    """Test that covered calls don't add to buying power in cash account"""
    from datetime import datetime, timedelta
    
    trades = [
        # Long Stock: 100 shares of IWM at $200
        Trade(
            symbol="IWM",
            quantity=100,
            price=200.0,
            side="buy",
            timestamp=datetime.now(),
            option_type="stock"
        ),
        # Short Covered Call: 1 contract of IWM 210C
        Trade(
            symbol="IWM",
            quantity=1,
            price=2.50,
            side="sell",
            timestamp=datetime.now(),
            option_type="call",
            strike_price=210.0,
            expiration_date=datetime.now() + timedelta(days=30)
        )
    ]
    
    # Account Value: $100,000
    # IWM Price: $205
    
    # Expected Capital:
    # Stock: 100 shares * $205 = $20,500
    # Covered Call: 0 (covered by stock, no additional margin needed)
    # Total: $20,500
    
    stats = calculate_capital_usage(
        trades, 
        account_value=100000.0, 
        current_prices={'IWM': 205.0}
    )
    
    assert stats['long_stock'] == 20500.0
    assert stats['cash_secured_puts'] == 0.0  # No CSPs
    assert stats['total_deployed'] == 20500.0  # Only stock capital
    assert stats['buying_power_usage_pct'] == 0.205
    assert stats['stock_positions']['IWM'] == 100

def test_calculate_capital_usage_stock_and_csp():
    """Test stock position + cash secured puts"""
    from datetime import datetime, timedelta
    
    trades = [
        # Long Stock: 100 shares of IWM at $200
        Trade(
            symbol="IWM",
            quantity=100,
            price=200.0,
            side="buy",
            timestamp=datetime.now(),
            option_type="stock"
        ),
        # Short Put: 1 contract of IWM 190P (Cash Secured)
        Trade(
            symbol="IWM",
            quantity=1,
            price=1.50,
            side="sell",
            timestamp=datetime.now(),
            option_type="put",
            strike_price=190.0,
            expiration_date=datetime.now() + timedelta(days=30)
        )
    ]
    
    # Account Value: $100,000
    # IWM Price: $205
    
    # Expected Capital:
    # Stock: 100 shares * $205 = $20,500
    # Put: 1 contract * 100 * $190 Strike = $19,000
    # Total: $39,500
    
    stats = calculate_capital_usage(
        trades, 
        account_value=100000.0, 
        current_prices={'IWM': 205.0}
    )
    
    assert stats['long_stock'] == 20500.0
    assert stats['cash_secured_puts'] == 19000.0
    assert stats['total_deployed'] == 39500.0
    assert stats['buying_power_usage_pct'] == 0.395
    assert stats['stock_positions']['IWM'] == 100

def test_calculate_capital_usage_multiple_csps():
    """Test multiple cash secured puts"""
    from datetime import datetime, timedelta
    
    trades = [
        # Short Put: 2 contracts of IWM 190P
        Trade(
            symbol="IWM",
            quantity=2,
            price=1.50,
            side="sell",
            timestamp=datetime.now(),
            option_type="put",
            strike_price=190.0,
            expiration_date=datetime.now() + timedelta(days=30)
        ),
        # Short Put: 1 contract of IWM 195P
        Trade(
            symbol="IWM",
            quantity=1,
            price=2.00,
            side="sell",
            timestamp=datetime.now(),
            option_type="put",
            strike_price=195.0,
            expiration_date=datetime.now() + timedelta(days=30)
        )
    ]
    
    # Expected Capital:
    # Put 1: 2 contracts * 100 * $190 = $38,000
    # Put 2: 1 contract * 100 * $195 = $19,500
    # Total: $57,500
    
    stats = calculate_capital_usage(
        trades, 
        account_value=100000.0, 
        current_prices={'IWM': 205.0}
    )
    
    assert stats['long_stock'] == 0.0
    assert stats['cash_secured_puts'] == 57500.0
    assert stats['total_deployed'] == 57500.0
    assert stats['buying_power_usage_pct'] == 0.575