from typing import List
from .models import Trade


def cost_basis(trades: List[Trade]) -> dict[str, float]:
    """
    Calculate cost basis metrics for a list of trades.
    
    Returns:
        dict with keys:
        - shares: current share position (positive = long, negative = short)
        - basis_without_premium: cost basis excluding option premiums
        - basis_with_premium: cost basis including option premiums
        - net_premium: total option premiums received/paid
    """
    shares = 0.0
    basis_without_premium = 0.0
    net_premium = 0.0
    
    for trade in trades:
        # Check if this is an option trade
        is_option = trade.strategy and ("put" in trade.strategy.lower() or "call" in trade.strategy.lower())
        
        if trade.side == "buy":
            if is_option:
                # Option purchase - only affects premium, not shares
                net_premium -= trade.quantity * trade.price  # Premium paid
            else:
                # Stock purchase - affects shares and basis
                shares += trade.quantity
                basis_without_premium += trade.quantity * trade.price
                
        elif trade.side == "sell":
            if is_option:
                # Option sale - only affects premium, not shares
                net_premium += trade.quantity * trade.price  # Premium received
            else:
                # Stock sale - affects shares and basis
                shares -= trade.quantity
                if shares + trade.quantity > 0:  # Only if we had shares to sell
                    # Calculate average cost basis for remaining shares
                    avg_basis = basis_without_premium / (shares + trade.quantity)
                    basis_without_premium = avg_basis * shares
    
    # Calculate basis with premium
    basis_with_premium = basis_without_premium - net_premium
    
    return {
        'shares': shares,
        'basis_without_premium': basis_without_premium,
        'basis_with_premium': basis_with_premium,
        'net_premium': net_premium
    } 