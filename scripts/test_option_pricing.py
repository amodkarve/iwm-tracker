#!/usr/bin/env python3
"""Quick test of option pricing"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.strategy.fuzzy_backtest import FuzzyBacktestEngine

engine = FuzzyBacktestEngine(initial_capital=1_000_000.0)

# Test realistic scenarios
current_price = 400.0
vix = 20.0

print("Option Pricing Test")
print("=" * 60)
print(f"Underlying: ${current_price:.2f}, VIX: {vix:.2f}")
print()

for dte in [7, 14, 21]:
    print(f"DTE: {dte} days")
    for moneyness in [-1.0, 0.0, 1.0, 2.0]:
        strike_offset = moneyness * current_price * 0.02
        strike = current_price - strike_offset
        price = engine._estimate_option_price(current_price, strike, 'put', dte, vix, moneyness)
        price_per_contract = price * 100
        print(f"  Moneyness={moneyness:4.1f}, Strike=${strike:6.2f}, Price=${price:6.3f}/share (${price_per_contract:6.2f}/contract)")
    print()

