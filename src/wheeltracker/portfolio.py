"""
Portfolio PnL calculations
"""
from typing import List, Dict, Optional
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from .models import Trade
from .calculations import cost_basis
from market_data import get_iwm_price


def calculate_closed_pnl(trades: List[Trade]) -> float:
    """
    Calculate closed (realized) PnL from all trades.
    
    This includes:
    - Realized gains/losses from stock sales
    - Net premium from closed option positions
    
    Args:
        trades: List of all trades
        
    Returns:
        Total closed PnL (realized profit/loss)
    """
    if not trades:
        return 0.0
    
    total_closed_pnl = 0.0
    
    # Group trades by symbol
    symbols = set(trade.symbol for trade in trades)
    
    for symbol in symbols:
        symbol_trades = [trade for trade in trades if trade.symbol == symbol]
        
        # Separate stock and option trades
        stock_trades = [t for t in symbol_trades if not t.option_type]
        option_trades = [t for t in symbol_trades if t.option_type]
        
        # Calculate closed PnL from stock trades (realized gains/losses)
        if stock_trades:
            stock_basis = cost_basis(stock_trades, use_wheel_strategy=False)
            total_closed_pnl += stock_basis['realized_gains_losses']
        
        # Calculate closed PnL from closed option positions
        # Group option trades by contract
        option_positions = {}
        for trade in option_trades:
            key = (
                trade.symbol,
                trade.strike_price,
                trade.expiration_date.date() if trade.expiration_date else None,
                trade.option_type
            )
            if key not in option_positions:
                option_positions[key] = {
                    'net_qty': 0,
                    'trades': []
                }
            
            if trade.side == 'buy':
                option_positions[key]['net_qty'] += trade.quantity
            else:
                option_positions[key]['net_qty'] -= trade.quantity
            
            option_positions[key]['trades'].append(trade)
        
        # Calculate PnL for closed option positions (net quantity = 0)
        for key, pos_data in option_positions.items():
            if pos_data['net_qty'] == 0:  # Closed position
                position_pnl = sum(
                    t.quantity * t.price * 100 * (1 if t.side == "sell" else -1)
                    for t in pos_data['trades']
                )
                total_closed_pnl += position_pnl
    
    return total_closed_pnl


def calculate_open_pnl(trades: List[Trade], current_prices: Optional[Dict[str, float]] = None) -> float:
    """
    Calculate open (unrealized) PnL from current positions.
    
    This includes:
    - Unrealized gains/losses on stock positions (current value - cost basis)
    - Unrealized gains/losses on open option positions (current value - cost basis)
    
    Args:
        trades: List of all trades
        current_prices: Dict mapping symbol to current price. If None, will fetch IWM price.
        
    Returns:
        Total open PnL (unrealized profit/loss)
    """
    if not trades:
        return 0.0
    
    if current_prices is None:
        iwm_price = get_iwm_price() or 0.0
        current_prices = {'IWM': iwm_price}
    
    total_open_pnl = 0.0
    symbols = set(trade.symbol for trade in trades)
    
    for symbol in symbols:
        symbol_trades = [trade for trade in trades if trade.symbol == symbol]
        basis_info = cost_basis(symbol_trades, use_wheel_strategy=True)
        
        # Calculate open PnL for stock positions
        if basis_info['shares'] > 0:
            current_price = current_prices.get(symbol, 0.0)
            current_value = basis_info['shares'] * current_price
            cost_basis_value = basis_info['basis_with_premium'] * basis_info['shares']
            stock_open_pnl = current_value - cost_basis_value
            total_open_pnl += stock_open_pnl
        
        # Calculate open PnL for open option positions
        # Group option trades by contract
        option_positions = {}
        for trade in symbol_trades:
            if trade.option_type:
                key = (
                    trade.symbol,
                    trade.strike_price,
                    trade.expiration_date.date() if trade.expiration_date else None,
                    trade.option_type
                )
                if key not in option_positions:
                    option_positions[key] = {
                        'net_qty': 0,
                        'trades': []
                    }
                
                if trade.side == 'buy':
                    option_positions[key]['net_qty'] += trade.quantity
                else:
                    option_positions[key]['net_qty'] -= trade.quantity
                
                option_positions[key]['trades'].append(trade)
        
        # Calculate PnL for open option positions
        # For simplicity, we'll use intrinsic value for options
        # In a real system, you'd fetch current option prices
        current_stock_price = current_prices.get(symbol, 0.0)
        
        for key, pos_data in option_positions.items():
            if pos_data['net_qty'] != 0:  # Open position
                symbol, strike, exp, opt_type = key
                
                # Calculate cost basis for this option position
                position_cost = sum(
                    t.quantity * t.price * 100 * (1 if t.side == "buy" else -1)
                    for t in pos_data['trades']
                )
                
                # Calculate current value (intrinsic value approximation)
                # For puts: max(0, strike - current_price) * 100 * contracts
                # For calls: max(0, current_price - strike) * 100 * contracts
                if opt_type == 'put':
                    intrinsic_value = max(0, strike - current_stock_price) * 100
                else:  # call
                    intrinsic_value = max(0, current_stock_price - strike) * 100
                
                current_value = intrinsic_value * abs(pos_data['net_qty'])
                
                # For short positions, PnL is inverted
                if pos_data['net_qty'] < 0:  # Short position
                    option_pnl = position_cost - current_value
                else:  # Long position
                    option_pnl = current_value - position_cost
                
                total_open_pnl += option_pnl
    
    return total_open_pnl


def calculate_nav(
    starting_value: float,
    trades: List[Trade],
    current_prices: Optional[Dict[str, float]] = None
) -> Dict[str, float]:
    """
    Calculate Net Asset Value (NAV) of the portfolio.
    
    NAV = Starting Portfolio Value + Open PnL + Closed PnL
    
    Args:
        starting_value: Starting portfolio value
        trades: List of all trades
        current_prices: Dict mapping symbol to current price
        
    Returns:
        Dict with:
        - nav: Net Asset Value
        - starting_value: Starting portfolio value
        - open_pnl: Open (unrealized) PnL
        - closed_pnl: Closed (realized) PnL
    """
    closed_pnl = calculate_closed_pnl(trades)
    open_pnl = calculate_open_pnl(trades, current_prices)
    nav = starting_value + open_pnl + closed_pnl
    
    return {
        'nav': nav,
        'starting_value': starting_value,
        'open_pnl': open_pnl,
        'closed_pnl': closed_pnl
    }

