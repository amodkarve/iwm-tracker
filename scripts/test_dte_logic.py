#!/usr/bin/env python3
"""Test 1 DTE / 3 DTE Friday logic"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date, timedelta
from src.strategy.fuzzy_backtest import FuzzyBacktestEngine

engine = FuzzyBacktestEngine(initial_capital=1_000_000.0)

# Test various dates
test_dates = [
    date(2024, 1, 1),   # Monday
    date(2024, 1, 2),   # Tuesday
    date(2024, 1, 3),   # Wednesday
    date(2024, 1, 4),   # Thursday
    date(2024, 1, 5),   # Friday
]

print("DTE Logic Test")
print("=" * 60)
for d in test_dates:
    if d.weekday() == 4:  # Friday
        dte = 3
        expiration = d + timedelta(days=3)
    else:
        dte = 1
        expiration = d + timedelta(days=1)
    
    weekday_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][d.weekday()]
    print(f"{weekday_name} {d}: DTE = {dte}, Expires {expiration}")

