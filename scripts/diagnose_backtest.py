#!/usr/bin/env python3
"""
Diagnostic script to identify issues with backtest performance

Checks:
1. Why trades aren't executing
2. Option pricing accuracy
3. Trade frequency
4. Premium collection
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date, timedelta
import pandas as pd
import numpy as np
from src.strategy.fuzzy_backtest import FuzzyBacktestEngine, FuzzyBacktestParams
from src.market_data.historical_data import get_combined_market_data, get_vix_history
from src.strategy.fuzzy_strategy import FuzzyStrategy
from src.strategy.fuzzy_inputs import normalize_vix, calculate_trend_normalized, calculate_cycle_normalized
from src.indicators.ehlers_trend import calculate_instantaneous_trend
from src.indicators.cycle_swing import calculate_cycle_swing

def diagnose_backtest():
    """Run diagnostic checks on backtest"""
    
    print("=" * 60)
    print("BACKTEST DIAGNOSTIC ANALYSIS")
    print("=" * 60)
    
    # Use optimized parameters from the run
    params = FuzzyBacktestParams(
        cycle_oversold_threshold=-0.4077562241484616,
        cycle_overbought_threshold=0.3304849415973333,
        trend_down_threshold=-0.1833457357336019,
        trend_up_threshold=0.4478102950930213,
        put_moneyness_weight=0.7806609741926838,
        put_size_weight=0.9537943888916242,
        call_sell_threshold=0.6430419389218128,
        hedge_score_threshold=0.5360401307953431,
        target_dte=14,
        hedge_dte=21,
        max_hedge_notional_pct=0.5539475154514801,
        target_daily_premium_pct=0.0010458654192343755,
        min_contract_premium=73.53895304782965,
        hedge_otm_pct_low_vix=13.212217760196193,
        hedge_otm_pct_high_vix=5.495712096619677,
    )
    
    engine = FuzzyBacktestEngine(
        initial_capital=1_000_000.0,
        params=params,
        use_spy=True
    )
    
    # Test period
    start_date = date(2021, 1, 1)
    end_date = date(2021, 3, 31)  # Just 3 months for diagnosis
    
    print(f"\nAnalyzing period: {start_date} to {end_date}")
    print(f"Initial capital: ${engine.initial_capital:,.0f}")
    print(f"Target daily premium: {params.target_daily_premium_pct*100:.4f}% = ${engine.initial_capital * params.target_daily_premium_pct:.2f}/day")
    print(f"Min contract premium: ${params.min_contract_premium:.2f}")
    print(f"Target DTE: {params.target_dte} days")
    
    # Get market data
    market_data = get_combined_market_data(start_date, end_date, True)
    if market_data.empty:
        print("ERROR: No market data available")
        return
    
    vix_history = get_vix_history(start_date, end_date)
    
    # Get indicator data
    indicator_start = start_date - timedelta(days=100)
    indicator_data = get_combined_market_data(indicator_start, end_date, True)
    close_prices = indicator_data['Close']
    hl2_prices = (indicator_data['High'] + indicator_data['Low']) / 2
    
    print(f"\nMarket data: {len(market_data)} trading days")
    print(f"SPY price range: ${market_data['Close'].min():.2f} - ${market_data['Close'].max():.2f}")
    print(f"VIX range: {market_data['VIX'].min():.2f} - {market_data['VIX'].max():.2f}")
    
    # Track diagnostics
    trade_attempts = 0
    trade_successes = 0
    trade_failures = {
        'premium_too_low': 0,
        'size_frac_too_low': 0,
        'no_remaining_target': 0,
        'no_contracts': 0,
        'insufficient_bp': 0
    }
    
    fuzzy_strategy = FuzzyStrategy()
    
    # Sample a few days
    sample_days = 0
    max_samples = 20
    
    for current_date in pd.date_range(start=start_date, end=end_date, freq='D'):
        current_date = current_date.date()
        
        if current_date not in market_data.index.date:
            continue
        
        if sample_days >= max_samples:
            break
        
        day_data = market_data.loc[market_data.index.date == current_date]
        if day_data.empty:
            continue
        
        current_price = float(day_data['Close'].iloc[0])
        current_vix = float(day_data['VIX'].iloc[0]) if 'VIX' in day_data.columns and pd.notna(day_data['VIX'].iloc[0]) else 20.0
        
        # Get indicators
        if current_date in close_prices.index.date:
            date_idx = list(close_prices.index.date).index(current_date)
            if date_idx >= 50:
                recent_hl2 = hl2_prices.iloc[max(0, date_idx-100):date_idx+1]
                recent_close = close_prices.iloc[max(0, date_idx-100):date_idx+1]
                trend = calculate_trend_normalized(recent_hl2)
                cycle = calculate_cycle_normalized(recent_close)
            else:
                trend = 0.0
                cycle = 0.0
        else:
            trend = 0.0
            cycle = 0.0
        
        vix_norm = normalize_vix(current_vix, vix_history)
        portfolio_metrics = engine._calculate_portfolio_metrics_for_fuzzy(current_price, current_vix)
        
        # Calculate fuzzy outputs
        put_moneyness = fuzzy_strategy.calculate_put_moneyness(cycle, trend) * params.put_moneyness_weight
        put_size_frac = fuzzy_strategy.calculate_put_size_frac(
            portfolio_metrics['premium_gap'],
            vix_norm,
            portfolio_metrics['bp_frac']
        ) * params.put_size_weight
        put_size_frac = min(1.0, put_size_frac)
        
        # Check if trade would execute
        if put_size_frac > 0.1:
            trade_attempts += 1
            
            # Simulate trade execution logic
            strike_offset = put_moneyness * current_price * 0.02
            target_strike = current_price - strike_offset
            target_strike = round(target_strike / 0.5) * 0.5
            
            expiration = current_date + timedelta(days=params.target_dte)
            option_price = engine._estimate_option_price(
                current_price, target_strike, 'put', params.target_dte, current_vix, put_moneyness
            )
            
            if option_price < params.min_contract_premium / 100:
                trade_failures['premium_too_low'] += 1
                if sample_days < max_samples:
                    print(f"\n{sample_days+1}. {current_date}: Trade blocked - Premium too low")
                    print(f"   Option price: ${option_price*100:.2f}, Min required: ${params.min_contract_premium:.2f}")
                    print(f"   Strike: ${target_strike:.2f}, Price: ${current_price:.2f}, VIX: {current_vix:.2f}")
                sample_days += 1
                continue
            
            total_value = engine.portfolio.total_value(current_price)
            target_premium = total_value * params.target_daily_premium_pct
            remaining_target = target_premium - engine.portfolio.daily_premium_collected
            
            if remaining_target <= 0:
                trade_failures['no_remaining_target'] += 1
                continue
            
            target_notional = remaining_target * put_size_frac
            contracts = int(target_notional / (option_price * 100))
            
            if contracts <= 0:
                trade_failures['no_contracts'] += 1
                if sample_days < max_samples:
                    print(f"\n{sample_days+1}. {current_date}: Trade blocked - No contracts")
                    print(f"   Target notional: ${target_notional:.2f}, Option price: ${option_price*100:.2f}")
                    print(f"   Put size frac: {put_size_frac:.3f}, Remaining target: ${remaining_target:.2f}")
                sample_days += 1
                continue
            
            required_bp = target_strike * 100 * contracts
            available_bp = engine.portfolio.buying_power_available(total_value, current_price)
            
            if required_bp > available_bp:
                trade_failures['insufficient_bp'] += 1
                if sample_days < max_samples:
                    print(f"\n{sample_days+1}. {current_date}: Trade blocked - Insufficient BP")
                    print(f"   Required: ${required_bp:,.0f}, Available: ${available_bp:,.0f}")
                sample_days += 1
                continue
            
            # Trade would execute
            trade_successes += 1
            if sample_days < max_samples:
                print(f"\n{sample_days+1}. {current_date}: Trade WOULD EXECUTE")
                print(f"   Strike: ${target_strike:.2f}, Contracts: {contracts}, Premium: ${option_price*100*contracts:.2f}")
                print(f"   Put size frac: {put_size_frac:.3f}, Moneyness: {put_moneyness:.2f}")
            sample_days += 1
            
            # Actually execute to update portfolio
            engine._execute_put_sale(current_price, current_vix, put_moneyness, put_size_frac, current_date)
        else:
            if sample_days < max_samples and trade_attempts == 0:
                print(f"\n{sample_days+1}. {current_date}: No trade - Size frac too low ({put_size_frac:.3f})")
                print(f"   Premium gap: {portfolio_metrics['premium_gap']:.3f}, BP frac: {portfolio_metrics['bp_frac']:.3f}, VIX norm: {vix_norm:.3f}")
                sample_days += 1
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    print(f"Trade attempts: {trade_attempts}")
    print(f"Trade successes: {trade_successes}")
    print(f"Trade failures:")
    for reason, count in trade_failures.items():
        if count > 0:
            print(f"  {reason}: {count}")
    
    print(f"\nSuccess rate: {trade_successes/trade_attempts*100:.1f}%" if trade_attempts > 0 else "\nNo trade attempts")
    
    # Check option pricing
    print("\n" + "=" * 60)
    print("OPTION PRICING ANALYSIS")
    print("=" * 60)
    
    sample_price = 400.0
    sample_vix = 20.0
    
    for dte in [7, 14, 21]:
        for moneyness in [-1.0, 0.0, 1.0, 2.0]:
            strike_offset = moneyness * sample_price * 0.02
            strike = sample_price - strike_offset
            price = engine._estimate_option_price(sample_price, strike, 'put', dte, sample_vix, moneyness)
            print(f"DTE={dte:2d}, Moneyness={moneyness:4.1f}, Strike=${strike:6.2f}, Price=${price*100:6.2f}")
    
    print("\n" + "=" * 60)
    print("KEY FINDINGS")
    print("=" * 60)
    
    if trade_failures['premium_too_low'] > 0:
        print(f"⚠️  {trade_failures['premium_too_low']} trades blocked by min_contract_premium (${params.min_contract_premium:.2f})")
        print("   Consider lowering min_contract_premium or improving option pricing model")
    
    if trade_failures['no_contracts'] > 0:
        print(f"⚠️  {trade_failures['no_contracts']} trades blocked - contracts <= 0")
        print("   This suggests put_size_frac is too low or option prices are too high")
    
    if trade_failures['insufficient_bp'] > 0:
        print(f"⚠️  {trade_failures['insufficient_bp']} trades blocked by buying power constraints")
        print("   Strategy may be too aggressive or BP calculation needs review")
    
    if trade_attempts == 0:
        print("⚠️  NO TRADE ATTEMPTS - put_size_frac never > 0.1")
        print("   Check fuzzy logic outputs and thresholds")

if __name__ == "__main__":
    diagnose_backtest()

