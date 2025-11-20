"""
Performance Analytics

Calculate performance metrics to track progress toward 18-20% annual return goal
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.wheeltracker.models import Trade


def calculate_daily_return(
    trades: List[Trade],
    account_value: float,
    date: Optional[datetime] = None
) -> float:
    """
    Calculate daily return from trades
    
    Args:
        trades: List of trades for the day
        account_value: Current account value
        date: Date to calculate for (default: today)
    
    Returns:
        Daily return as percentage (e.g., 0.0008 for 0.08%)
    """
    if not trades or account_value <= 0:
        return 0.0
    
    if date is None:
        date = datetime.now()
    
    # Filter trades for the specific date
    day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    
    day_trades = [
        t for t in trades 
        if day_start <= t.timestamp < day_end
    ]
    
    if not day_trades:
        return 0.0
    
    # Calculate net premium for the day
    daily_premium = 0.0
    for trade in day_trades:
        if trade.option_type:  # Only count option trades
            multiplier = 1 if trade.side == "sell" else -1
            daily_premium += trade.quantity * trade.price * 100 * multiplier
    
    return daily_premium / account_value


def calculate_annual_return(
    trades: List[Trade],
    start_date: datetime,
    end_date: datetime,
    initial_account_value: float
) -> Dict[str, float]:
    """
    Calculate annualized return
    
    Args:
        trades: All trades in the period
        start_date: Start date
        end_date: End date
        initial_account_value: Starting account value
    
    Returns:
        Dictionary with:
        - total_return: Total return as percentage
        - annualized_return: Annualized return percentage
        - days: Number of days in period
        - total_premium: Total premium collected
    """
    if not trades or initial_account_value <= 0:
        return {
            'total_return': 0.0,
            'annualized_return': 0.0,
            'days': 0,
            'total_premium': 0.0
        }
    
    # Filter trades in date range
    period_trades = [
        t for t in trades
        if start_date <= t.timestamp <= end_date
    ]
    
    # Calculate total premium
    total_premium = 0.0
    for trade in period_trades:
        if trade.option_type:
            multiplier = 1 if trade.side == "sell" else -1
            total_premium += trade.quantity * trade.price * 100 * multiplier
    
    # Calculate returns
    total_return = total_premium / initial_account_value
    
    # Annualize
    days = (end_date - start_date).days
    if days > 0:
        annualized_return = (1 + total_return) ** (365 / days) - 1
    else:
        annualized_return = 0.0
    
    return {
        'total_return': total_return,
        'annualized_return': annualized_return,
        'days': days,
        'total_premium': total_premium
    }


def calculate_sharpe_ratio(
    daily_returns: pd.Series,
    risk_free_rate: float = 0.04
) -> float:
    """
    Calculate Sharpe ratio (risk-adjusted return)
    
    Args:
        daily_returns: Series of daily returns
        risk_free_rate: Annual risk-free rate (default 4%)
    
    Returns:
        Sharpe ratio
    """
    if daily_returns.empty or len(daily_returns) < 2:
        return 0.0
    
    # Convert annual risk-free rate to daily
    daily_rf = (1 + risk_free_rate) ** (1/252) - 1
    
    # Calculate excess returns
    excess_returns = daily_returns - daily_rf
    
    # Calculate Sharpe ratio
    if excess_returns.std() == 0:
        return 0.0
    
    sharpe = excess_returns.mean() / excess_returns.std()
    
    # Annualize (multiply by sqrt of trading days)
    return sharpe * np.sqrt(252)


def calculate_max_drawdown(account_values: pd.Series) -> Dict[str, float]:
    """
    Calculate maximum drawdown
    
    Args:
        account_values: Series of account values over time
    
    Returns:
        Dictionary with:
        - max_drawdown: Maximum drawdown as percentage
        - max_drawdown_dollars: Maximum drawdown in dollars
        - peak_value: Peak account value
        - trough_value: Trough account value
    """
    if account_values.empty:
        return {
            'max_drawdown': 0.0,
            'max_drawdown_dollars': 0.0,
            'peak_value': 0.0,
            'trough_value': 0.0
        }
    
    # Calculate running maximum
    running_max = account_values.expanding().max()
    
    # Calculate drawdown
    drawdown = (account_values - running_max) / running_max
    
    # Find maximum drawdown
    max_dd_idx = drawdown.idxmin()
    max_dd = drawdown.min()
    
    # Find peak before max drawdown
    peak_idx = account_values[:max_dd_idx].idxmax()
    peak_value = account_values[peak_idx]
    trough_value = account_values[max_dd_idx]
    
    return {
        'max_drawdown': abs(max_dd),
        'max_drawdown_dollars': peak_value - trough_value,
        'peak_value': peak_value,
        'trough_value': trough_value
    }


def calculate_win_rate(trades: List[Trade]) -> Dict[str, float]:
    """
    Calculate win rate for closed positions
    
    Args:
        trades: List of all trades
    
    Returns:
        Dictionary with:
        - win_rate: Percentage of winning trades
        - total_trades: Total number of closed trades
        - winning_trades: Number of winning trades
        - losing_trades: Number of losing trades
        - avg_win: Average winning trade P&L
        - avg_loss: Average losing trade P&L
    """
    # Group trades by option contract (symbol, strike, expiration, type)
    from collections import defaultdict
    
    positions = defaultdict(list)
    
    for trade in trades:
        if trade.option_type:
            key = (
                trade.symbol,
                trade.strike_price,
                trade.expiration_date.date() if trade.expiration_date else None,
                trade.option_type
            )
            positions[key].append(trade)
    
    # Calculate P&L for each closed position
    wins = []
    losses = []
    
    for position_trades in positions.values():
        # Calculate net quantity
        net_qty = sum(
            t.quantity * (1 if t.side == "buy" else -1)
            for t in position_trades
        )
        
        # If net quantity is 0, position is closed
        if net_qty == 0:
            # Calculate P&L
            pnl = sum(
                t.quantity * t.price * 100 * (1 if t.side == "sell" else -1)
                for t in position_trades
            )
            
            if pnl > 0:
                wins.append(pnl)
            elif pnl < 0:
                losses.append(abs(pnl))
    
    total_trades = len(wins) + len(losses)
    
    if total_trades == 0:
        return {
            'win_rate': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'avg_win': 0.0,
            'avg_loss': 0.0
        }
    
    return {
        'win_rate': len(wins) / total_trades,
        'total_trades': total_trades,
        'winning_trades': len(wins),
        'losing_trades': len(losses),
        'avg_win': np.mean(wins) if wins else 0.0,
        'avg_loss': np.mean(losses) if losses else 0.0
    }


def get_performance_summary(
    trades: List[Trade],
    account_value: float,
    initial_account_value: float,
    start_date: Optional[datetime] = None
) -> Dict[str, any]:
    """
    Get comprehensive performance summary
    
    Args:
        trades: All trades
        account_value: Current account value
        initial_account_value: Starting account value
        start_date: Start date (default: first trade date)
    
    Returns:
        Dictionary with all performance metrics
    """
    if not trades:
        return {
            'error': 'No trades available'
        }
    
    if start_date is None:
        start_date = min(t.timestamp for t in trades)
    
    end_date = datetime.now()
    
    # Calculate annual return
    annual_metrics = calculate_annual_return(
        trades, start_date, end_date, initial_account_value
    )
    
    # Calculate win rate
    win_metrics = calculate_win_rate(trades)
    
    # Calculate progress toward goal (18-20%)
    target_min = 0.18
    target_max = 0.20
    current_annual = annual_metrics['annualized_return']
    
    progress_pct = (current_annual / target_max) * 100 if target_max > 0 else 0
    on_track = target_min <= current_annual <= target_max
    
    return {
        **annual_metrics,
        **win_metrics,
        'current_account_value': account_value,
        'initial_account_value': initial_account_value,
        'total_gain': account_value - initial_account_value,
        'total_gain_pct': (account_value - initial_account_value) / initial_account_value,
        'target_annual_min': target_min,
        'target_annual_max': target_max,
        'progress_to_goal': progress_pct,
        'on_track': on_track,
        'days_active': (end_date - start_date).days
    }
