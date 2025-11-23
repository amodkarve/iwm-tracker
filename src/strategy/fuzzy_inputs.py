"""
Helper functions to calculate fuzzy logic inputs from portfolio data
"""
from typing import Dict, List, Optional, Tuple
from datetime import date, datetime, timedelta
import logging
import pandas as pd

from src.wheeltracker.models import Trade
from src.wheeltracker.calculations import cost_basis
from src.wheeltracker.analytics import trades_to_dataframe
from src.strategy.position_manager import calculate_capital_usage, get_current_positions
from src.market_data import get_iwm_price
from src.indicators import get_trend_signal, get_momentum_signal
from src.market_data.price_fetcher import get_hl2_series, get_price_series

logger = logging.getLogger(__name__)


def normalize_vix(vix_value: float, vix_history: Optional[pd.Series] = None) -> float:
    """
    Normalize VIX to [0, 1] using percentile of historical range
    
    Args:
        vix_value: Current VIX value
        vix_history: Historical VIX series (optional, for percentile calculation)
        
    Returns:
        Normalized VIX in [0, 1]
    """
    if vix_history is not None and len(vix_history) > 0:
        vix_min = vix_history.min()
        vix_max = vix_history.max()
        if vix_max > vix_min:
            normalized = (vix_value - vix_min) / (vix_max - vix_min)
            return max(0.0, min(1.0, normalized))
    
    # Fallback: use typical VIX range (10-40)
    vix_min = 10.0
    vix_max = 40.0
    normalized = (vix_value - vix_min) / (vix_max - vix_min)
    return max(0.0, min(1.0, normalized))


def calculate_trend_normalized(hl2_series: pd.Series) -> float:
    """
    Calculate normalized trend from Ehlers indicator
    
    Args:
        hl2_series: HL2 price series
        
    Returns:
        Normalized trend in [-1, 1] where -1 = down, +1 = up
    """
    if hl2_series.empty or len(hl2_series) < 50:
        return 0.0
    
    try:
        trend_signal = get_trend_signal(hl2_series)
        # Convert discrete signal to normalized value
        # We can also calculate slope from trendline for more granular value
        from src.indicators.ehlers_trend import calculate_instantaneous_trend
        result = calculate_instantaneous_trend(hl2_series)
        
        if result['trendline'].empty or result['smooth'].empty:
            return float(trend_signal)
        
        # Calculate slope from recent trendline values
        recent_trend = result['trendline'].tail(10)
        if len(recent_trend) > 1:
            slope = (recent_trend.iloc[-1] - recent_trend.iloc[0]) / recent_trend.iloc[0]
            # Normalize slope to [-1, 1]
            normalized = max(-1.0, min(1.0, slope * 10))  # Scale factor
            return normalized
        
        return float(trend_signal)
    except Exception as e:
        logger.warning(f"Error calculating trend: {e}")
        return 0.0


def calculate_cycle_normalized(price_series: pd.Series) -> float:
    """
    Calculate normalized cycle swing momentum
    
    Args:
        price_series: Close price series
        
    Returns:
        Normalized cycle in [-1, 1] where -1 = oversold, +1 = overbought
    """
    if price_series.empty or len(price_series) < 50:
        return 0.0
    
    try:
        from src.indicators.cycle_swing import calculate_cycle_swing
        result = calculate_cycle_swing(price_series)
        
        if result['csi'].empty:
            return 0.0
        
        csi_value = result['csi'].iloc[-1]
        
        # Normalize CSI to [-1, 1] using bands
        if not result['high_band'].empty and not result['low_band'].empty:
            high_band = result['high_band'].iloc[-1]
            low_band = result['low_band'].iloc[-1]
            
            if pd.notna(high_band) and pd.notna(low_band) and (high_band - low_band) > 0:
                normalized = 2 * (csi_value - low_band) / (high_band - low_band) - 1
                return max(-1.0, min(1.0, normalized))
        
        # Fallback: use signal
        momentum_signal = get_momentum_signal(price_series)
        return float(momentum_signal)
    except Exception as e:
        logger.warning(f"Error calculating cycle: {e}")
        return 0.0


def calculate_portfolio_metrics(
    trades: List[Trade],
    account_value: float,
    current_prices: Optional[Dict[str, float]] = None
) -> Dict[str, float]:
    """
    Calculate portfolio metrics for fuzzy logic inputs
    
    Args:
        trades: List of all trades
        account_value: Total account value
        current_prices: Dict mapping symbol to current price
        
    Returns:
        Dictionary with:
        - bp_frac: Buying power fraction (0-1)
        - stock_weight: Stock weight in portfolio (0-1)
        - delta_port: Portfolio delta normalized (approximate)
        - premium_gap: Premium gap (0-1)
    """
    if current_prices is None:
        iwm_price = get_iwm_price() or 0.0
        current_prices = {'IWM': iwm_price}
    
    # Calculate capital usage
    capital_stats = calculate_capital_usage(trades, account_value, current_prices)
    
    # Buying power fraction
    bp_usage = capital_stats.get('buying_power_usage_pct', 0.0)
    bp_frac = 1.0 - bp_usage  # Available buying power fraction
    bp_frac = max(0.0, min(1.0, bp_frac))
    
    # Stock weight
    stock_capital = capital_stats.get('long_stock', 0.0)
    stock_weight = stock_capital / account_value if account_value > 0 else 0.0
    stock_weight = max(0.0, min(1.0, stock_weight))
    
    # Portfolio delta (simplified - would need option positions for accurate calculation)
    # For now, approximate: long stock = positive delta, short puts = positive delta
    delta_port = stock_weight  # Simplified approximation
    # Could be enhanced with actual option delta calculations
    
    # Premium gap calculation
    # Target: 0.08% of portfolio per day
    from src.strategy.rules import TARGET_DAILY_PREMIUM_PCT
    target_premium_per_day = account_value * TARGET_DAILY_PREMIUM_PCT
    
    # Calculate realized premium (from closed option positions)
    # This is a simplified calculation
    realized_premium = 0.0
    df = trades_to_dataframe(trades) if trades else pd.DataFrame()
    
    if not df.empty:
        # Sum premium from closed option positions
        closed_options = df[
            (df['option_type'].isin(['put', 'call'])) &
            (df['side'] == 'sell')
        ]
        if not closed_options.empty:
            # Rough estimate: sum of sell prices
            realized_premium = closed_options['price'].sum() * 100  # Per contract
    
    # Calculate premium gap
    if target_premium_per_day > 0:
        premium_gap = max(0.0, 1.0 - (realized_premium / target_premium_per_day))
    else:
        premium_gap = 1.0  # Far below if no target
    
    premium_gap = max(0.0, min(1.0, premium_gap))
    
    return {
        'bp_frac': bp_frac,
        'stock_weight': stock_weight,
        'delta_port': delta_port,
        'premium_gap': premium_gap
    }


def calculate_assigned_share_metrics(
    trades: List[Trade],
    symbol: str,
    current_price: float
) -> Dict[str, float]:
    """
    Calculate metrics for assigned shares
    
    Args:
        trades: List of all trades
        symbol: Symbol (e.g., 'IWM')
        current_price: Current stock price
        
    Returns:
        Dictionary with:
        - unreal_pnl_pct: Unrealized PnL as % of cost basis
        - iv_rank: IV rank (0-1) - placeholder, would need IV data
        - days_since_assignment: Days since assignment
    """
    symbol_trades = [t for t in trades if t.symbol == symbol]
    
    if not symbol_trades:
        return {
            'unreal_pnl_pct': 0.0,
            'iv_rank': 0.5,
            'days_since_assignment': 0,
            'cost_basis': current_price
        }
    
    # Normalize trades: cost_basis expects option_type=None for stock trades
    # but tests may use option_type='stock', so we need to handle both
    from src.wheeltracker.models import Trade
    normalized_trades = []
    for trade in symbol_trades:
        # If option_type is 'stock' or not in ['put', 'call'], treat as stock (None)
        if trade.option_type == 'stock' or (trade.option_type is not None and trade.option_type not in ['put', 'call']):
            # Create a new Trade object with option_type=None
            normalized_trade = Trade(
                id=trade.id,
                symbol=trade.symbol,
                quantity=trade.quantity,
                price=trade.price,
                side=trade.side,
                timestamp=trade.timestamp,
                strategy=trade.strategy,
                option_type=None,  # Normalize to None for stock
                strike_price=trade.strike_price,
                expiration_date=trade.expiration_date
            )
            normalized_trades.append(normalized_trade)
        else:
            normalized_trades.append(trade)
    
    # Calculate cost basis
    basis_info = cost_basis(normalized_trades, use_wheel_strategy=True)
    
    if basis_info['shares'] <= 0:
        return {
            'unreal_pnl_pct': 0.0,
            'iv_rank': 0.5,
            'days_since_assignment': 0,
            'cost_basis': current_price
        }
    
    cost_basis_per_share = basis_info['basis_with_premium']
    
    # Unrealized PnL %
    # Handle edge cases: if cost basis is 0 or negative, use basis without premium
    if cost_basis_per_share <= 0:
        cost_basis_per_share = basis_info.get('basis_without_premium', current_price)
    
    if cost_basis_per_share > 0:
        unreal_pnl_pct = (current_price - cost_basis_per_share) / cost_basis_per_share
    else:
        unreal_pnl_pct = 0.0
    
    # Days since assignment (find most recent stock purchase)
    # Note: cost_basis treats option_type=None as stock, but tests use option_type='stock'
    assignment_date = None
    for trade in sorted(symbol_trades, key=lambda x: x.timestamp, reverse=True):
        # Check if this is a stock trade (either None or 'stock' or not an option type)
        is_stock = (trade.option_type is None or 
                   trade.option_type == 'stock' or 
                   trade.option_type not in ['put', 'call'])
        if is_stock and trade.side == 'buy':
            assignment_date = trade.timestamp.date() if isinstance(trade.timestamp, datetime) else trade.timestamp
            break
    
    days_since_assignment = 0
    if assignment_date:
        days_since_assignment = (date.today() - assignment_date).days
    
    # IV rank (placeholder - would need IV history)
    iv_rank = 0.5  # Default to medium
    
    return {
        'unreal_pnl_pct': unreal_pnl_pct,
        'iv_rank': iv_rank,
        'days_since_assignment': days_since_assignment,
        'cost_basis': cost_basis_per_share
    }


def get_fuzzy_inputs(
    trades: List[Trade],
    account_value: float,
    vix_value: Optional[float] = None,
    vix_history: Optional[pd.Series] = None,
    current_prices: Optional[Dict[str, float]] = None
) -> Dict[str, float]:
    """
    Calculate all fuzzy logic inputs from portfolio and market data
    
    Args:
        trades: List of all trades
        account_value: Total account value
        vix_value: Current VIX value (optional)
        vix_history: Historical VIX series (optional)
        current_prices: Dict mapping symbol to current price
        
    Returns:
        Dictionary with all fuzzy inputs:
        - trend: Normalized trend (-1 to +1)
        - cycle: Normalized cycle (-1 to +1)
        - vix_norm: Normalized VIX (0-1)
        - bp_frac: Buying power fraction (0-1)
        - stock_weight: Stock weight (0-1)
        - delta_port: Portfolio delta normalized
        - premium_gap: Premium gap (0-1)
    """
    # Get market indicators
    trend = 0.0
    cycle = 0.0
    
    try:
        hl2_series = get_hl2_series(period="3mo")
        if not hl2_series.empty:
            trend = calculate_trend_normalized(hl2_series)
        
        price_series = get_price_series(period="3mo")
        if not price_series.empty:
            cycle = calculate_cycle_normalized(price_series)
    except Exception as e:
        logger.warning(f"Error calculating indicators: {e}")
    
    # Normalize VIX
    vix_norm = 0.5  # Default
    if vix_value is not None:
        vix_norm = normalize_vix(vix_value, vix_history)
    
    # Calculate portfolio metrics
    portfolio_metrics = calculate_portfolio_metrics(trades, account_value, current_prices)
    
    return {
        'trend': trend,
        'cycle': cycle,
        'vix_norm': vix_norm,
        **portfolio_metrics
    }

