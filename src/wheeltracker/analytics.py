import pandas as pd
from typing import List
from .models import Trade


def trades_to_dataframe(trades: List[Trade]) -> pd.DataFrame:
    """Convert list of trades to pandas DataFrame."""
    if not trades:
        return pd.DataFrame()

    data = []
    for trade in trades:
        data.append(
            {
                "id": trade.id,
                "symbol": trade.symbol,
                "quantity": trade.quantity,
                "price": trade.price,
                "side": trade.side,
                "timestamp": trade.timestamp,
                "strategy": trade.strategy,
                "expiration_date": trade.expiration_date,
                "strike_price": trade.strike_price,
                "option_type": trade.option_type,
            }
        )

    return pd.DataFrame(data)


def monthly_net_premium(df: pd.DataFrame) -> pd.Series:
    """Calculate net premium by month from trade DataFrame."""
    if df.empty:
        return pd.Series(dtype=float)

    # Filter for option trades only
    option_trades = df[df["option_type"].notna()].copy()

    if option_trades.empty:
        return pd.Series(dtype=float)

    # Calculate premium for each trade (positive for sell, negative for buy)
    option_trades["premium"] = option_trades.apply(
        lambda row: row["quantity"]
        * row["price"]
        * 100
        * (1 if row["side"] == "sell" else -1),
        axis=1,
    )

    # Group by month and sum premiums
    option_trades["month"] = option_trades["timestamp"].dt.to_period("M")
    monthly_premium = option_trades.groupby("month")["premium"].sum()

    return monthly_premium


def cumulative_net_premium(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate cumulative net premium over time."""
    if df.empty:
        return pd.DataFrame()

    # Filter for option trades only
    option_trades = df[df["option_type"].notna()].copy()

    if option_trades.empty:
        return pd.DataFrame()

    # Calculate premium for each trade
    option_trades["premium"] = option_trades.apply(
        lambda row: row["quantity"]
        * row["price"]
        * 100
        * (1 if row["side"] == "sell" else -1),
        axis=1,
    )

    # Sort by timestamp and calculate cumulative sum
    option_trades = option_trades.sort_values("timestamp")
    option_trades["cumulative_premium"] = option_trades["premium"].cumsum()

    return option_trades[["timestamp", "cumulative_premium"]]


def open_option_obligations(df: pd.DataFrame) -> pd.DataFrame:
    """Get open option obligations (quantity != 0) grouped by strike/expiry."""
    if df.empty:
        return pd.DataFrame()

    # Filter for option trades only
    option_trades = df[df["option_type"].notna()].copy()

    if option_trades.empty:
        return pd.DataFrame()

    # Calculate net quantity for each option contract
    option_trades["net_quantity"] = option_trades.apply(
        lambda row: row["quantity"] * (1 if row["side"] == "buy" else -1), axis=1
    )

    # Group by symbol, strike, expiration, and option type
    obligations = (
        option_trades.groupby(
            ["symbol", "strike_price", "expiration_date", "option_type"]
        )["net_quantity"]
        .sum()
        .reset_index()
    )

    # Filter for open positions (net_quantity != 0)
    open_positions = obligations[obligations["net_quantity"] != 0].copy()

    if open_positions.empty:
        return pd.DataFrame()

    # Sort by symbol and expiration
    open_positions = open_positions.sort_values(
        ["symbol", "expiration_date", "strike_price"]
    )

    return open_positions
