"""
Comprehensive Trade Recommendation Engine

Generates recommendations for:
1. Rolling existing positions (puts/calls)
2. Opening new positions (puts/covered calls)
3. Hedging (protective puts)
4. Call substitution (stock replacement)
"""
import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd

from src.wheeltracker.models import Trade
from src.wheeltracker.analytics import get_open_option_positions_for_closing, trades_to_dataframe
from src.market_data import get_iwm_price, get_1dte_puts_near_money
from .trade_recommendations import (
    TradeRecommendation,
    get_hedging_recommendation,
    get_stock_replacement_recommendation,
    get_position_sizing_recommendation,
    _calculate_confidence,
    _generate_reason
)
from .position_manager import calculate_capital_usage, get_current_positions
from src.market_data.price_fetcher import get_hl2_series, get_price_series
from src.indicators import get_trend_signal, get_momentum_signal

logger = logging.getLogger(__name__)


class RecommendationType:
    """Recommendation action types"""
    ROLL = "roll"
    OPEN_PUT = "open_put"
    OPEN_COVERED_CALL = "open_covered_call"
    HEDGE = "hedge"
    SUBSTITUTE = "substitute"


def get_all_recommendations(
    trades: List[Trade],
    account_value: float = 1000000.0,
    max_recommendations: int = 10
) -> List[TradeRecommendation]:
    """
    Get comprehensive trade recommendations across all strategies
    
    Args:
        trades: List of all trades from database
        account_value: Total account value
        max_recommendations: Maximum recommendations to return
        
    Returns:
        Sorted list of recommendations by priority
    """
    all_recommendations = []
    
    # Get market data
    iwm_price = get_iwm_price()
    if not iwm_price:
        logger.warning("Cannot get recommendations without IWM price")
        return []
    
    # Get market indicators
    trend_signal = 0
    momentum_signal = 0
    
    try:
        hl2_series = get_hl2_series(period="3mo")
        if not hl2_series.empty:
            trend_signal = get_trend_signal(hl2_series)
        
        price_series = get_price_series(period="3mo")
        if not price_series.empty:
            momentum_signal = get_momentum_signal(price_series)
    except Exception as e:
        logger.warning(f"Error calculating indicators: {e}")
    
    # Calculate capital usage
    capital_stats = calculate_capital_usage(trades, account_value, {'IWM': iwm_price})
    current_positions = get_current_positions(trades)
    
    # 1. ROLLING RECOMMENDATIONS (Highest Priority)
    rolling_recs = get_rolling_recommendations(trades, iwm_price, account_value)
    all_recommendations.extend(rolling_recs)
    
    # 2. HEDGING RECOMMENDATIONS (High Priority - Risk Management)
    hedge_rec = get_hedging_recommendation(
        account_value,
        current_positions,
        trend_signal,
        momentum_signal,
        iwm_price
    )
    if hedge_rec:
        hedge_rec.action_type = RecommendationType.HEDGE
        all_recommendations.append(hedge_rec)
    
    # 3. CALL SUBSTITUTION (High Priority - Capital Management)
    substitute_rec = get_stock_replacement_recommendation(
        account_value,
        capital_stats,
        trend_signal,
        iwm_price
    )
    if substitute_rec:
        substitute_rec.action_type = RecommendationType.SUBSTITUTE
        all_recommendations.append(substitute_rec)
    
    # 4. COVERED CALL RECOMMENDATIONS (Medium Priority)
    covered_call_recs = get_covered_call_recommendations(
        current_positions,
        iwm_price,
        trend_signal,
        account_value
    )
    all_recommendations.extend(covered_call_recs)
    
    # 5. NEW PUT SALES (Standard Priority)
    new_put_recs = get_new_put_recommendations(
        iwm_price,
        trend_signal,
        momentum_signal,
        account_value
    )
    all_recommendations.extend(new_put_recs)
    
    # Sort by priority and quality
    all_recommendations.sort(
        key=lambda x: (
            _get_priority_score(x.action_type),
            {'high': 3, 'medium': 2, 'low': 1}.get(x.confidence, 0),
            x.expected_premium if x.expected_premium > 0 else -x.expected_premium
        ),
        reverse=True
    )
    
    return all_recommendations[:max_recommendations]


def _get_priority_score(action_type: str) -> int:
    """Get priority score for recommendation type"""
    priority_map = {
        RecommendationType.ROLL: 100,        # Highest - manage existing
        RecommendationType.HEDGE: 90,        # High - risk management
        RecommendationType.SUBSTITUTE: 85,   # High - capital management
        RecommendationType.OPEN_COVERED_CALL: 70,  # Medium - income
        RecommendationType.OPEN_PUT: 50      # Standard - new positions
    }
    return priority_map.get(action_type, 0)


def get_rolling_recommendations(
    trades: List[Trade],
    iwm_price: float,
    account_value: float
) -> List[TradeRecommendation]:
    """
    Generate rolling recommendations for profitable positions near expiration
    
    Logic:
    - Position is 0-1 DTE
    - Position is profitable (can close for less than sold)
    - New option has sufficient premium (≥50% of original)
    """
    recommendations = []
    
    # Convert trades to DataFrame for analysis
    df = trades_to_dataframe(trades)
    
    if df.empty:
        return recommendations
    
    # Get open positions
    open_positions = get_open_option_positions_for_closing(df)
    
    if open_positions.empty:
        return recommendations
    
    # Initialize Market Data client for real-time pricing
    from src.market_data.marketdata_client import MarketDataClient
    md_client = MarketDataClient()
    
    # Analyze each open position
    for _, position in open_positions.iterrows():
        # Only consider short positions (we sold them)
        if position['net_quantity'] >= 0:
            continue
        
        # Check if near expiration (0-2 DTE)
        exp_date = position['expiration_date']
        if isinstance(exp_date, str):
            exp_date = pd.to_datetime(exp_date)
        
        dte = (exp_date.date() - date.today()).days
        
        if dte > 2:
            continue
        
        # Calculate if position is profitable
        # Get original entry price from trades
        position_trades = df[
            (df['symbol'] == position['symbol']) &
            (df['strike_price'] == position['strike_price']) &
            (df['expiration_date'] == position['expiration_date']) &
            (df['option_type'] == position['option_type'])
        ]
        
        if position_trades.empty:
            continue
        
        # Calculate average entry price for short positions
        short_trades = position_trades[position_trades['side'] == 'sell']
        if short_trades.empty:
            continue
        
        avg_entry_price = (short_trades['price'] * short_trades['quantity']).sum() / short_trades['quantity'].sum()
        
        # Get CURRENT price from Market Data API
        try:
            # Fetch current option chain for this specific option
            exp_str = exp_date.strftime('%Y-%m-%d')
            current_chain = md_client.get_options_chain(
                symbol=position['symbol'],
                expiration=exp_str,
                strike_min=position['strike_price'] - 0.01,
                strike_max=position['strike_price'] + 0.01,
                option_type=position['option_type']
            )
            
            if current_chain.empty:
                logger.warning(f"No current price data for {position['symbol']} {position['strike_price']} {position['option_type']}")
                continue
            
            # Get the mid price for current position
            current_price = current_chain.iloc[0]['mid']
            
        except Exception as e:
            logger.error(f"Error fetching current option price: {e}")
            continue
        
        # Check if profitable (current price < entry price)
        profit_per_contract = (avg_entry_price - current_price) * 100
        
        if profit_per_contract <= 0:
            continue  # Not profitable, don't roll
        
        # Get NEW options at similar strike for rolling
        # Fetch next available expiration (1-5 DTE)
        try:
            new_chain = md_client.get_options_chain(
                symbol=position['symbol'],
                strike_min=position['strike_price'] - 0.5,
                strike_max=position['strike_price'] + 0.5,
                dte_min=1,
                dte_max=5,
                option_type=position['option_type']
            )
            
            if new_chain.empty:
                logger.warning(f"No new options available for rolling {position['symbol']}")
                continue
            
            # Filter to closest expiration
            new_chain['expiration'] = pd.to_datetime(new_chain['expiration'])
            next_expiration = new_chain['expiration'].min()
            new_chain = new_chain[new_chain['expiration'] == next_expiration]
            
            # Find option closest to same strike
            new_chain['strike_diff'] = abs(new_chain['strike'] - position['strike_price'])
            new_chain = new_chain.sort_values('strike_diff')
            
            if new_chain.empty:
                continue
            
            new_option = new_chain.iloc[0]
            new_price = new_option['mid']
            new_strike = new_option['strike']
            
        except Exception as e:
            logger.error(f"Error fetching new option for rolling: {e}")
            continue
        
        # Check if new premium is sufficient (≥50% of original)
        if new_price < avg_entry_price * 0.5:
            logger.info(f"New premium ${new_price:.2f} is less than 50% of original ${avg_entry_price:.2f}, skipping roll")
            continue
        
        # Calculate net credit from roll
        net_credit = (new_price - current_price) * 100 * abs(position['net_quantity'])
        
        # Create rolling recommendation
        rec = TradeRecommendation(
            symbol=position['symbol'],
            option_symbol=new_option['option_symbol'],
            strike=new_strike,
            expiration=next_expiration.date(),
            option_type=position['option_type'],
            bid=new_option['bid'],
            ask=new_option['ask'],
            mid=new_price,
            recommended_price=new_price,
            recommended_contracts=int(abs(position['net_quantity'])),
            expected_premium=net_credit,
            premium_pct=(net_credit / account_value) * 100,
            delta=new_option.get('delta'),
            iv=new_option.get('iv'),
            volume=new_option.get('volume'),
            open_interest=new_option.get('open_interest'),
            reason=f"🔄 ROLL: Close ${current_price:.2f} (${profit_per_contract:.0f} profit) → Open ${new_price:.2f} = ${net_credit:.0f} net credit. {dte} DTE remaining.",
            confidence="high",
            action_type=RecommendationType.ROLL
        )
        
        recommendations.append(rec)
    
    return recommendations



def get_covered_call_recommendations(
    current_positions: Dict,
    iwm_price: float,
    trend_signal: int,
    account_value: float
) -> List[TradeRecommendation]:
    """
    Generate covered call recommendations if holding stock
    
    Logic:
    - Must own at least 100 shares
    - Prefer neutral to slightly bearish trends
    - Target 1-2% OTM for monthly, or ATM for weekly
    """
    recommendations = []
    
    stock_positions = current_positions.get('stock', {})
    iwm_shares = stock_positions.get('IWM', 0)
    
    if iwm_shares < 100:
        return recommendations
    
    # Don't sell calls in strong uptrend (want to keep upside)
    if trend_signal > 0:
        return recommendations
    
    # Calculate how many calls we can sell
    contracts_available = iwm_shares // 100
    
    # Target strike: 1% OTM for weekly
    target_strike = iwm_price * 1.01
    target_strike = round(target_strike)  # Round to nearest dollar
    
    # Estimate premium (would need real market data)
    # Weekly ATM/slightly OTM calls typically 0.3-0.5% of stock price
    estimated_price = iwm_price * 0.004  # 0.4% estimate
    
    expiration_date = date.today() + timedelta(days=7)
    
    expected_premium = estimated_price * 100 * contracts_available
    
    rec = TradeRecommendation(
        symbol='IWM',
        option_symbol=f"IWM{expiration_date.strftime('%y%m%d')}C{int(target_strike*1000):08d}",
        strike=target_strike,
        expiration=expiration_date,
        option_type='call',
        bid=estimated_price * 0.95,
        ask=estimated_price * 1.05,
        mid=estimated_price,
        recommended_price=estimated_price,
        recommended_contracts=contracts_available,
        expected_premium=expected_premium,
        premium_pct=(expected_premium / account_value) * 100,
        reason=f"📞 COVERED CALL: Generate income on {iwm_shares} shares. {((target_strike - iwm_price) / iwm_price * 100):.1f}% OTM.",
        confidence="medium",
        action_type=RecommendationType.OPEN_COVERED_CALL
    )
    
    recommendations.append(rec)
    
    return recommendations


def get_new_put_recommendations(
    iwm_price: float,
    trend_signal: int,
    momentum_signal: int,
    account_value: float,
    max_recommendations: int = 3
) -> List[TradeRecommendation]:
    """
    Generate new put sale recommendations (existing logic)
    """
    recommendations = []
    
    # Get 1 DTE puts
    puts = get_1dte_puts_near_money(iwm_price)
    
    if puts.empty:
        logger.warning("No puts available for new recommendations")
        return recommendations
    
    # CRITICAL: Filter out unreasonable strikes
    # For selling puts, we want strikes BELOW current price (OTM)
    # Typically 1-5% OTM is reasonable
    min_strike = iwm_price * 0.90  # 10% OTM minimum
    max_strike = iwm_price * 1.02  # Slightly above current (max 2% ITM)
    
    puts = puts[
        (puts['strike'] >= min_strike) & 
        (puts['strike'] <= max_strike)
    ]
    
    if puts.empty:
        logger.warning(f"No reasonable strikes found. IWM: ${iwm_price:.2f}, Range: ${min_strike:.2f} - ${max_strike:.2f}")
        return recommendations
    
    logger.info(f"Found {len(puts)} puts in reasonable strike range ${min_strike:.2f} - ${max_strike:.2f}")
    
    # Analyze each put option
    for _, put in puts.iterrows():
        # Additional validation: skip if strike is way off
        if put['strike'] > iwm_price * 1.05 or put['strike'] < iwm_price * 0.85:
            logger.warning(f"Skipping unreasonable strike ${put['strike']:.2f} (IWM: ${iwm_price:.2f})")
            continue
        
        # Calculate position sizing
        sizing = get_position_sizing_recommendation(put['mid'], account_value)
        
        # Determine confidence
        confidence = _calculate_confidence(
            put, trend_signal, momentum_signal, iwm_price
        )
        
        # Generate reason
        reason = _generate_reason(
            put, trend_signal, momentum_signal, sizing, iwm_price
        )
        
        expiration_date = date.today() + timedelta(days=1)
        
        # Create recommendation
        rec = TradeRecommendation(
            symbol='IWM',
            option_symbol=put['option_symbol'],
            strike=put['strike'],
            expiration=expiration_date,
            option_type='put',
            bid=put['bid'],
            ask=put['ask'],
            mid=put['mid'],
            recommended_price=put['mid'],
            recommended_contracts=sizing['contracts'],
            expected_premium=sizing['expected_premium'],
            premium_pct=sizing['premium_pct'],
            delta=put.get('delta'),
            iv=put.get('iv'),
            volume=put.get('volume'),
            open_interest=put.get('open_interest'),
            reason=reason,
            confidence=confidence,
            action_type=RecommendationType.OPEN_PUT
        )
        
        recommendations.append(rec)
    
    return recommendations[:max_recommendations]

