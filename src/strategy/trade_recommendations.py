"""
Trade Recommendation Engine

Suggests trades based on:
- Market data (IWM price, options chain)
- Technical indicators (Ehler's Trend, Cycle Swing)
- Strategy rules (0.08% daily premium target)
"""
import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Optional
import logging

from market_data import get_iwm_price, get_1dte_puts_near_money, get_data_source
from indicators import calculate_instantaneous_trend, calculate_cycle_swing, get_trend_signal, get_momentum_signal
from market_data.price_fetcher import get_hl2_series, get_price_series
from strategy.premium_calculator import get_position_sizing_recommendation
from strategy.rules import (
    TARGET_DAILY_PREMIUM_PCT,
    CLOSE_THRESHOLD,
    MIN_CONTRACTS,
    MAX_CONTRACTS,
    DEFAULT_ACCOUNT_SIZE
)


logger = logging.getLogger(__name__)


class TradeRecommendation:
    """Represents a trade recommendation"""
    
    def __init__(
        self,
        symbol: str,
        option_symbol: str,
        strike: float,
        expiration: date,
        option_type: str,
        bid: float,
        ask: float,
        mid: float,
        recommended_price: float,
        recommended_contracts: int,
        expected_premium: float,
        premium_pct: float,
        delta: Optional[float] = None,
        iv: Optional[float] = None,
        volume: Optional[int] = None,
        open_interest: Optional[int] = None,
        reason: str = "",
        confidence: str = "medium"
    ):
        self.symbol = symbol
        self.option_symbol = option_symbol
        self.strike = strike
        self.expiration = expiration
        self.option_type = option_type
        self.bid = bid
        self.ask = ask
        self.mid = mid
        self.recommended_price = recommended_price
        self.recommended_contracts = recommended_contracts
        self.expected_premium = expected_premium
        self.premium_pct = premium_pct
        self.delta = delta
        self.iv = iv
        self.volume = volume
        self.open_interest = open_interest
        self.reason = reason
        self.confidence = confidence
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for display"""
        return {
            'symbol': self.symbol,
            'option_symbol': self.option_symbol,
            'strike': self.strike,
            'expiration': self.expiration,
            'option_type': self.option_type,
            'bid': self.bid,
            'ask': self.ask,
            'mid': self.mid,
            'recommended_price': self.recommended_price,
            'recommended_contracts': self.recommended_contracts,
            'expected_premium': self.expected_premium,
            'premium_pct': self.premium_pct,
            'delta': self.delta,
            'iv': self.iv,
            'volume': self.volume,
            'open_interest': self.open_interest,
            'reason': self.reason,
            'confidence': self.confidence
        }


def get_trade_recommendations(
    account_value: float = DEFAULT_ACCOUNT_SIZE,
    max_recommendations: int = 3
) -> List[TradeRecommendation]:
    """
    Get trade recommendations for selling 1 DTE puts
    
    Args:
        account_value: Account value for position sizing
        max_recommendations: Maximum number of recommendations to return
    
    Returns:
        List of TradeRecommendation objects, sorted by confidence
    """
    recommendations = []
    
    # Get current IWM price
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
    
    # Get 1 DTE puts
    data_source = get_data_source()
    
    if data_source == 'marketdata':
        # Use Market Data App for options chain
        puts = get_1dte_puts_near_money(iwm_price)
        
        if puts.empty:
            logger.warning("No 1 DTE puts available from Market Data App")
            return []
        
        # Analyze each put option
        for _, put in puts.iterrows():
            # Calculate position sizing
            sizing = get_position_sizing_recommendation(put['mid'], account_value)
            
            # Determine confidence based on indicators and data quality
            confidence = _calculate_confidence(
                put, trend_signal, momentum_signal, iwm_price
            )
            
            # Generate reason
            reason = _generate_reason(
                put, trend_signal, momentum_signal, sizing, iwm_price
            )
            
            # For 1 DTE options, expiration should be tomorrow
            # Don't rely on Market Data App's expiration field which may be invalid
            from datetime import timedelta
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
                recommended_price=put['mid'],  # Start with mid price
                recommended_contracts=sizing['contracts'],
                expected_premium=sizing['expected_premium'],
                premium_pct=sizing['premium_pct'],
                delta=put.get('delta'),
                iv=put.get('iv'),
                volume=put.get('volume'),
                open_interest=put.get('open_interest'),
                reason=reason,
                confidence=confidence
            )
            
            recommendations.append(rec)
    
    else:
        # Fallback: Create synthetic recommendation based on IWM price
        # Since we don't have options data, suggest typical strikes
        atm_strike = round(iwm_price)
        
        # Estimate option price (very rough - 0.08% of strike as starting point)
        estimated_price = atm_strike * TARGET_DAILY_PREMIUM_PCT * 100
        
        sizing = get_position_sizing_recommendation(estimated_price, account_value)
        
        # For 1 DTE options, expiration should be tomorrow
        from datetime import timedelta
        expiration_date = date.today() + timedelta(days=1)
        
        rec = TradeRecommendation(
            symbol='IWM',
            option_symbol=f"IWM{expiration_date.strftime('%y%m%d')}P{int(atm_strike*1000):08d}",
            strike=atm_strike,
            expiration=expiration_date,
            option_type='put',
            bid=estimated_price * 0.95,
            ask=estimated_price * 1.05,
            mid=estimated_price,
            recommended_price=estimated_price,
            recommended_contracts=sizing['contracts'],
            expected_premium=sizing['expected_premium'],
            premium_pct=sizing['premium_pct'],
            delta=None,
            iv=None,
            volume=None,
            open_interest=None,
            reason="⚠️ Using estimated pricing (Market Data App not configured). Sign up for real-time data!",
            confidence="low"
        )
        
        recommendations.append(rec)
    
    # Sort by confidence and premium
    recommendations.sort(
        key=lambda x: (
            {'high': 3, 'medium': 2, 'low': 1}.get(x.confidence, 0),
            x.expected_premium
        ),
        reverse=True
    )
    
    return recommendations[:max_recommendations]


def _calculate_confidence(
    put: pd.Series,
    trend_signal: int,
    momentum_signal: int,
    iwm_price: float
) -> str:
    """Calculate confidence level for a recommendation"""
    score = 0
    
    # Trend alignment (bullish trend = good for selling puts)
    if trend_signal > 0:
        score += 2
    elif trend_signal == 0:
        score += 1
    
    # Momentum (not oversold = good)
    if momentum_signal >= 0:
        score += 1
    
    # Volume and open interest
    if pd.notna(put.get('volume')) and put.get('volume', 0) > 100:
        score += 1
    if pd.notna(put.get('open_interest')) and put.get('open_interest', 0) > 500:
        score += 1
    
    # Delta (prefer 0.20-0.40 delta)
    if pd.notna(put.get('delta')):
        delta_abs = abs(put['delta'])
        if 0.20 <= delta_abs <= 0.40:
            score += 2
        elif 0.15 <= delta_abs <= 0.50:
            score += 1
    
    # Strike relative to price (prefer slightly OTM)
    strike_pct = (iwm_price - put['strike']) / iwm_price
    if 0.01 <= strike_pct <= 0.03:  # 1-3% OTM
        score += 1
    
    # Convert score to confidence
    if score >= 6:
        return 'high'
    elif score >= 3:
        return 'medium'
    else:
        return 'low'


def _generate_reason(
    put: pd.Series,
    trend_signal: int,
    momentum_signal: int,
    sizing: Dict,
    iwm_price: float
) -> str:
    """Generate human-readable reason for recommendation"""
    reasons = []
    
    # Trend
    if trend_signal > 0:
        reasons.append("✅ Bullish trend")
    elif trend_signal < 0:
        reasons.append("⚠️ Bearish trend")
    else:
        reasons.append("➡️ Neutral trend")
    
    # Momentum
    if momentum_signal > 0:
        reasons.append("⚠️ Overbought")
    elif momentum_signal < 0:
        reasons.append("✅ Not oversold")
    else:
        reasons.append("➡️ Neutral momentum")
    
    # Premium target
    if sizing['premium_pct'] >= TARGET_DAILY_PREMIUM_PCT * 0.9:
        reasons.append(f"✅ Meets {TARGET_DAILY_PREMIUM_PCT*100:.2f}% target")
    else:
        reasons.append(f"⚠️ Below {TARGET_DAILY_PREMIUM_PCT*100:.2f}% target")
    
    # Delta
    if pd.notna(put.get('delta')):
        delta_abs = abs(put['delta'])
        if 0.20 <= delta_abs <= 0.40:
            reasons.append(f"✅ Good delta ({delta_abs:.2f})")
        else:
            reasons.append(f"➡️ Delta {delta_abs:.2f}")
    
    # Strike position
    strike_pct = (iwm_price - put['strike']) / iwm_price
    if strike_pct > 0:
        reasons.append(f"✅ {strike_pct*100:.1f}% OTM")
    else:
        reasons.append(f"⚠️ {abs(strike_pct)*100:.1f}% ITM")
    
    return " | ".join(reasons)
