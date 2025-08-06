import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, date
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from wheeltracker.db import db
from wheeltracker.models import Trade
from wheeltracker.calculations import cost_basis
from wheeltracker.analytics import (
    trades_to_dataframe,
    monthly_net_premium,
    cumulative_net_premium,
    open_option_obligations,
)


def main():
    st.title("🚀 Wheel Tracker")

    # Sidebar for adding trades
    with st.sidebar:
        st.header("Add New Trade")

        # Trade form
        with st.form("add_trade_form"):
            symbol = st.text_input("Symbol", placeholder="AAPL")

            # Trade type selection
            trade_type = st.selectbox(
                "Trade Type", ["stock", "put", "call"], help="Select the type of trade"
            )

            side = st.selectbox("Side", ["buy", "sell"])
            quantity = st.number_input("Quantity", min_value=1, value=1)
            price = st.number_input("Price", min_value=0.01, value=150.0, step=0.01)

            # Option-specific fields
            expiration_date = None
            strike_price = None
            option_type = None

            # Always show option contract details form
            st.write("**Option Contract Details**")
            expiration_date = st.date_input(
                "Expiration Date",
                value=date.today(),
                help="Option expiration date (ignored for stock trades)",
            )
            strike_price = st.number_input(
                "Strike Price",
                min_value=0.01,
                value=150.0,
                step=0.01,
                help="Option strike price (ignored for stock trades)",
            )

            strategy = st.text_input(
                "Strategy", placeholder="wheel", help="Trading strategy name"
            )

            submitted = st.form_submit_button("Add Trade")

            if submitted:
                if symbol and price > 0:
                    # Set option type based on trade type
                    option_type = trade_type if trade_type in ["put", "call"] else None

                    # Create trade object
                    trade = Trade(
                        symbol=symbol.upper(),
                        quantity=quantity,
                        price=price,
                        side=side,
                        timestamp=datetime.now(),
                        strategy=strategy if strategy else None,
                        expiration_date=(
                            datetime.combine(expiration_date, datetime.min.time())
                            if option_type
                            else None
                        ),
                        strike_price=strike_price if option_type else None,
                        option_type=option_type,
                    )

                    # Insert trade
                    try:
                        inserted_trade = db.insert_trade(trade)
                        st.success(
                            f"Trade added: {inserted_trade.symbol} {inserted_trade.side} {inserted_trade.quantity}"
                        )
                    except Exception as e:
                        st.error(f"Error adding trade: {e}")
                else:
                    st.error("Please fill in all required fields")

    # Main content area
    st.header("Trade History")

    # Get all trades
    try:
        trades = db.list_trades()

        if trades:
            # Convert trades to DataFrame for display
            trade_data = []
            for trade in trades:
                trade_data.append(
                    {
                        "ID": trade.id,
                        "Symbol": trade.symbol,
                        "Side": trade.side,
                        "Quantity": trade.quantity,
                        "Price": f"${trade.price:.2f}",
                        "Type": trade.option_type or "stock",
                        "Strike": (
                            f"${trade.strike_price:.2f}" if trade.strike_price else "-"
                        ),
                        "Expiration": (
                            trade.expiration_date.strftime("%Y-%m-%d")
                            if trade.expiration_date
                            else "-"
                        ),
                        "Strategy": trade.strategy or "-",
                        "Date": trade.timestamp.strftime("%Y-%m-%d %H:%M"),
                    }
                )

            df = pd.DataFrame(trade_data)
            st.dataframe(df, use_container_width=True)

            # Cost basis calculations
            st.header("Cost Basis Analysis")

            # Group trades by symbol
            symbols = set(trade.symbol for trade in trades)

            for symbol in sorted(symbols):
                symbol_trades = [trade for trade in trades if trade.symbol == symbol]
                basis = cost_basis(symbol_trades)

                st.subheader(f"{symbol} Position")

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        "Shares",
                        f"{basis['shares']:.0f}",
                        help="Current share position (positive = long, negative = short)",
                    )

                with col2:
                    st.metric(
                        "Basis (excl. premium)",
                        f"${basis['basis_without_premium']:.2f}",
                        help="Cost basis per share excluding option premiums",
                    )

                with col3:
                    st.metric(
                        "Basis (incl. premium)",
                        f"${basis['basis_with_premium']:.2f}",
                        help="Cost basis per share including option premiums",
                    )

                with col4:
                    st.metric(
                        "Net Premium",
                        f"${basis['net_premium']:.2f}",
                        help="Total option premiums received/paid",
                    )

            # Analytics and Charts
            st.header("Analytics & Insights")

            # Convert trades to DataFrame for analytics
            df = trades_to_dataframe(trades)

            if not df.empty:
                # Monthly Net Premium Chart
                monthly_premium = monthly_net_premium(df)
                if not monthly_premium.empty:
                    st.subheader("Monthly Net Premium")

                    # Convert to DataFrame for Altair
                    monthly_df = monthly_premium.reset_index()
                    monthly_df.columns = ["month", "premium"]
                    monthly_df["month"] = monthly_df["month"].astype(str)

                    chart = (
                        alt.Chart(monthly_df)
                        .mark_bar()
                        .encode(
                            x=alt.X("month:N", title="Month"),
                            y=alt.Y("premium:Q", title="Net Premium ($)"),
                            color=alt.condition(
                                alt.datum.premium > 0,
                                alt.value("green"),
                                alt.value("red"),
                            ),
                        )
                        .properties(width=600, height=300)
                    )

                    st.altair_chart(chart, use_container_width=True)

                # Cumulative Net Premium Chart
                cumulative_df = cumulative_net_premium(df)
                if not cumulative_df.empty:
                    st.subheader("Cumulative Net Premium")

                    chart = (
                        alt.Chart(cumulative_df)
                        .mark_line()
                        .encode(
                            x=alt.X("timestamp:T", title="Date"),
                            y=alt.Y(
                                "cumulative_premium:Q", title="Cumulative Premium ($)"
                            ),
                        )
                        .properties(width=600, height=300)
                    )

                    st.altair_chart(chart, use_container_width=True)

                # Open Option Obligations Table
                obligations_df = open_option_obligations(df)
                if not obligations_df.empty:
                    st.subheader("Open Option Obligations")

                    # Format the table for display
                    display_df = obligations_df.copy()
                    display_df["strike_price"] = display_df["strike_price"].apply(
                        lambda x: f"${x:.2f}"
                    )
                    display_df["expiration_date"] = display_df[
                        "expiration_date"
                    ].dt.strftime("%Y-%m-%d")
                    display_df["net_quantity"] = display_df["net_quantity"].apply(
                        lambda x: f"{x:+.0f}"
                    )
                    display_df.columns = [
                        "Symbol",
                        "Strike",
                        "Expiration",
                        "Type",
                        "Net Quantity",
                    ]

                    st.dataframe(display_df, use_container_width=True)
                else:
                    st.info("No open option obligations found.")
            else:
                st.info("No trades available for analytics.")

        else:
            st.info("No trades found. Add your first trade using the sidebar!")

    except Exception as e:
        st.error(f"Error loading trades: {e}")


if __name__ == "__main__":
    main()
