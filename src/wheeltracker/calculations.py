from typing import List
from .models import Trade


def cost_basis(trades: List[Trade]) -> dict[str, float]:
    """
    Calculate cost basis metrics for a list of trades.
    
    Returns:
        dict with keys:
        - shares: current share position (positive = long, negative = short)
        - basis_without_premium: cost basis per share excluding option premiums
        - basis_with_premium: cost basis per share including option premiums
        - net_premium: total option premiums received/paid
    """
    shares = 0.0
    basis_without_premium = 0.0
    net_premium = 0.0
    realized_gains_losses = 0.0  # Track realized gains/losses from stock sales
    
    for trade in trades:
        # Check if this is an option trade
        is_option = trade.option_type is not None
        
        if trade.side == "buy":
            if is_option:
                # Option purchase - only affects premium, not shares
                # Option prices are per share, but contracts are for 100 shares
                net_premium -= trade.quantity * trade.price * 100  # Premium paid
            else:
                # Stock purchase - affects shares and basis
                shares += trade.quantity
                basis_without_premium += trade.quantity * trade.price
                
        elif trade.side == "sell":
            if is_option:
                # Option sale - only affects premium, not shares
                # Option prices are per share, but contracts are for 100 shares
                net_premium += trade.quantity * trade.price * 100  # Premium received
            else:
                # Stock sale - affects shares and basis
                shares -= trade.quantity
                if shares + trade.quantity > 0:  # Only if we had shares to sell
                    # Calculate average cost basis for the shares being sold
                    avg_basis = basis_without_premium / (shares + trade.quantity)
                    shares_sold_basis = avg_basis * trade.quantity
                    
                    # Calculate realized gain/loss from the sale
                    sale_proceeds = trade.quantity * trade.price
                    realized_gain_loss = sale_proceeds - shares_sold_basis
                    realized_gains_losses += realized_gain_loss
                    
                    # Update basis for remaining shares
                    basis_without_premium = avg_basis * shares
    
    # Calculate basis with premium and realized gains/losses
    # When no shares remain, the basis reflects total profit/loss
    if shares > 0:
        basis_with_premium = basis_without_premium - net_premium
        basis_without_premium_per_share = basis_without_premium / shares
        basis_with_premium_per_share = basis_with_premium / shares
    else:
        # When no shares, basis reflects total profit/loss including realized gains/losses
        basis_without_premium_per_share = 0.0
        total_profit_loss = realized_gains_losses + net_premium
        basis_with_premium_per_share = -total_profit_loss  # Negative because profit is positive
    
    return {
        'shares': shares,
        'basis_without_premium': basis_without_premium_per_share,
        'basis_with_premium': basis_with_premium_per_share,
        'net_premium': net_premium
    } 