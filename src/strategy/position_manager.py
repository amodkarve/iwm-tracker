"""
Position Manager Module

Handles logic for:
- Tracking buying power usage
- Calculating capital deployed
- Validating trade feasibility based on account constraints
"""
from typing import List, Dict, Optional
import pandas as pd
from src.wheeltracker.models import Trade

def get_current_positions(trades: List[Trade]) -> Dict:
    """
    Calculate current positions from trade history.
    
    Returns:
        Dict with keys:
        - 'stock': Dict[symbol, shares]
        - 'options': List[Dict] (open option contracts)
        - 'cash': float (approximate, if we tracked it)
    """
    positions = {
        'stock': {},
        'options': []
    }
    
    # Sort trades by time
    sorted_trades = sorted(trades, key=lambda x: x.timestamp)
    
    for trade in sorted_trades:
        if trade.option_type == 'stock':
            current_shares = positions['stock'].get(trade.symbol, 0)
            if trade.side == 'buy':
                positions['stock'][trade.symbol] = current_shares + trade.quantity
            else:
                positions['stock'][trade.symbol] = current_shares - trade.quantity
        else:
            # For options, we need to track open contracts
            # This is a simplified view; a real system would match opening/closing trades
            # For now, we'll assume we can just sum quantities (buy=+1, sell=-1)
            # But options have expirations, so we need to filter out expired ones later
            # A better approach for this specific app might be to rely on the 'open_option_obligations' logic
            pass
            
    return positions

def calculate_capital_usage(
    trades: List[Trade], 
    account_value: float,
    current_prices: Dict[str, float]
) -> Dict:
    """
    Calculate how much capital is currently deployed.
    
    For covered calls: If you own stock and have short calls, the calls don't require
    additional margin - only the stock capital is counted.
    
    Args:
        trades: List of all trades
        account_value: Total account value (Net Liquidation Value)
        current_prices: Dict mapping symbol to current price
        
    Returns:
        Dict with:
        - 'cash_secured_puts': Capital reserved for CSPs
        - 'long_stock': Capital tied up in stock
        - 'total_deployed': Total capital used
        - 'buying_power_usage_pct': % of account used
    """
    # 1. Calculate Stock Capital
    stock_capital = 0.0
    stock_positions = {}
    
    for trade in trades:
        if trade.option_type == 'stock' or trade.option_type is None:
            current = stock_positions.get(trade.symbol, 0)
            if trade.side == 'buy':
                stock_positions[trade.symbol] = current + trade.quantity
            else:
                stock_positions[trade.symbol] = current - trade.quantity
    
    for symbol, shares in stock_positions.items():
        if shares > 0:
            price = current_prices.get(symbol, 0)
            stock_capital += shares * price
            
    # 2. Calculate CSP Capital (Cash Secured Puts)
    # We need to find OPEN short puts that are NOT covered by stock
    csp_capital = 0.0
    
    # Filter for puts that haven't expired
    from datetime import datetime
    today = datetime.now().date()
    
    # Group trades by option symbol to find net quantity
    option_positions = {}
    for trade in trades:
        if trade.option_type in ['put', 'call']:
            # Check expiration
            if trade.expiration_date and trade.expiration_date.date() >= today:
                # Construct unique key for the option
                key = f"{trade.symbol}_{trade.expiration_date}_{trade.strike_price}_{trade.option_type}"
                current = option_positions.get(key, {'qty': 0, 'strike': trade.strike_price, 'type': trade.option_type})
                
                if trade.side == 'sell':
                    current['qty'] -= trade.quantity # Short
                else:
                    current['qty'] += trade.quantity # Buy to close/open
                
                option_positions[key] = current

    # Calculate capital for short puts (CSPs)
    # For short calls: In a cash account, short calls must be covered by stock
    # Covered calls don't require additional margin beyond the stock capital
    # (The stock capital already accounts for the cash required to hold the shares)
    for key, pos in option_positions.items():
        if pos['type'] == 'put' and pos['qty'] < 0:
            # Short puts require cash = Strike * 100 * |Contracts|
            reserved = pos['strike'] * 100 * abs(pos['qty'])
            csp_capital += reserved
        elif pos['type'] == 'call' and pos['qty'] < 0:
            # Short calls in cash account: must be covered by stock
            # Extract symbol from key (format: symbol_expiration_strike_type)
            symbol = key.split('_')[0]
            shares_owned = stock_positions.get(symbol, 0)
            contracts_short = abs(pos['qty'])
            shares_needed = contracts_short * 100
            
            # In a cash account, all short calls must be covered by stock
            # Covered calls don't require additional margin beyond the stock
            # The stock capital already accounts for the cash required
            # No additional capital calculation needed for covered calls

    # Total deployed: stock capital + cash secured puts
    # Note: Covered calls don't require additional margin beyond the stock
    # (Stock capital already includes the cash required to hold the shares)
    total_deployed = stock_capital + csp_capital
    usage_pct = (total_deployed / account_value) if account_value > 0 else 0
    
    return {
        'cash_secured_puts': csp_capital,
        'long_stock': stock_capital,
        'total_deployed': total_deployed,
        'buying_power_usage_pct': usage_pct,
        'stock_positions': stock_positions # Return this for stock replacement logic
    }
