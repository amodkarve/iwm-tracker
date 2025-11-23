"""
Example: Using Fuzzy Logic Strategy for Trading Decisions

This example demonstrates how to use the fuzzy logic system to make
trading decisions based on market conditions and portfolio state.
"""
from src.strategy.fuzzy_strategy import FuzzyStrategy
from src.strategy.fuzzy_inputs import get_fuzzy_inputs
from src.strategy.fuzzy_recommendations import FuzzyRecommendationEngine
from src.wheeltracker.models import Trade


def example_fuzzy_put_decision():
    """Example: Calculate put selling decision using fuzzy logic"""
    
    # Initialize fuzzy strategy
    fuzzy = FuzzyStrategy()
    
    # Example market conditions
    cycle = -0.6  # Oversold
    trend = 0.4   # Slightly bullish
    
    # Calculate put moneyness recommendation
    put_moneyness = fuzzy.calculate_put_moneyness(cycle, trend)
    print(f"Put Moneyness: {put_moneyness:.2f}")
    print(f"  Negative = ITM, 0 = ATM, Positive = OTM")
    
    # Example portfolio state
    premium_gap = 0.7  # Far below target
    vix_norm = 0.3     # Low VIX
    bp_frac = 0.6      # Comfortable buying power
    
    # Calculate put size fraction
    put_size_frac = fuzzy.calculate_put_size_frac(premium_gap, vix_norm, bp_frac)
    print(f"\nPut Size Fraction: {put_size_frac:.2f}")
    print(f"  Fraction of target premium to chase: {put_size_frac*100:.0f}%")


def example_fuzzy_call_decision():
    """Example: Calculate call selling decision using fuzzy logic"""
    
    fuzzy = FuzzyStrategy()
    
    # Example assigned share metrics
    unreal_pnl_pct = 0.05   # 5% profit
    dist_from_be = 0.08     # 8% above breakeven
    iv_rank = 0.7           # High IV
    premium_yield = 0.02    # 2% annualized
    
    # Calculate call sell score
    call_sell_score = fuzzy.calculate_call_sell_score(
        unreal_pnl_pct, dist_from_be, iv_rank, premium_yield
    )
    print(f"\nCall Sell Score: {call_sell_score:.2f}")
    print(f"  Score > 0.6 = sell calls, < 0.6 = skip")
    
    # Calculate call moneyness
    cycle = 0.3   # Neutral to slightly overbought
    trend = 0.2   # Slightly bullish
    
    call_moneyness = fuzzy.calculate_call_moneyness(cycle, trend)
    print(f"\nCall Moneyness: {call_moneyness:.2f}")
    print(f"  0 = at breakeven, higher = further OTM")


def example_fuzzy_hedge_decision():
    """Example: Calculate hedge decision using fuzzy logic"""
    
    fuzzy = FuzzyStrategy()
    
    # Example market conditions
    vix_norm = 0.2    # Low VIX
    cycle = 0.7       # Overbought
    trend = 0.5       # Bullish
    stock_weight = 0.6  # Heavy stock position
    delta_port = 0.4    # Long delta
    
    # Calculate hedge score and OTM distance
    hedge_score, hedge_otm_pct = fuzzy.calculate_hedge_score(
        vix_norm, cycle, trend, stock_weight, delta_port
    )
    print(f"\nHedge Score: {hedge_score:.2f}")
    print(f"  Score > 0.4 = consider hedging")
    print(f"Hedge OTM %: {hedge_otm_pct:.1f}%")
    print(f"  Distance out of the money for hedge puts")


def example_fuzzy_conversion_decision():
    """Example: Calculate share to ITM call conversion decision"""
    
    fuzzy = FuzzyStrategy()
    
    # Example portfolio state
    bp_frac = 0.15      # Critical buying power
    stock_weight = 0.7  # Heavy stock position
    vix_norm = 0.4      # Medium VIX
    
    # Calculate conversion score
    convert_score, itm_depth = fuzzy.calculate_convert_score(
        bp_frac, stock_weight, vix_norm
    )
    print(f"\nConvert Score: {convert_score:.2f}")
    print(f"  Fraction of shares to convert to ITM calls")
    print(f"ITM Depth (Delta): {itm_depth:.2f}")
    print(f"  Target delta for ITM calls (0.7-0.9)")


def example_full_recommendation_engine():
    """Example: Using the full fuzzy recommendation engine"""
    
    # Initialize engine
    engine = FuzzyRecommendationEngine()
    
    # Example: Get put recommendations
    # (In real usage, you would pass actual trades and market data)
    print("\n=== Fuzzy Recommendation Engine ===")
    print("To use the full engine, call:")
    print("  engine.get_fuzzy_put_recommendations(trades, account_value, iwm_price)")
    print("  engine.get_fuzzy_call_recommendations(trades, account_value, iwm_price)")
    print("  engine.get_fuzzy_hedge_recommendations(trades, account_value, iwm_price)")


if __name__ == "__main__":
    print("=" * 60)
    print("Fuzzy Logic Strategy Examples")
    print("=" * 60)
    
    example_fuzzy_put_decision()
    example_fuzzy_call_decision()
    example_fuzzy_hedge_decision()
    example_fuzzy_conversion_decision()
    example_full_recommendation_engine()
    
    print("\n" + "=" * 60)
    print("For more details, see src/strategy/fuzzy_strategy.py")
    print("=" * 60)

