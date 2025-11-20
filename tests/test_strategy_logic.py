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

def test_stock_replacement_trigger():
    # Trigger: Bullish Trend (1) AND High Capital Usage (>75%) AND Long Stock
    
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
    assert rec.option_type == 'call'
    assert "STOCK REPLACEMENT" in rec.reason
    assert rec.strike < 200.0 # ITM Call

def test_stock_replacement_no_trigger_low_usage():
    # No Trigger: Low Capital Usage (50%)
    
    capital_stats = {
        'buying_power_usage_pct': 0.50,
        'stock_positions': {'IWM': 100}
    }
    
    rec = get_stock_replacement_recommendation(
        account_value=100000.0,
        capital_usage=capital_stats,
        trend_signal=1,
        iwm_price=200.0
    )
    
    assert rec is None
