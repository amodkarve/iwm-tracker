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
    get_open_option_positions_for_closing,
)

# Configure page
st.set_page_config(
    page_title="Wheel Tracker",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown(
    """
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
        font-size: 2.5rem;
        font-weight: bold;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    
    .section-header {
        background: linear-gradient(90deg, #f093fb 0%, #f5576c 100%);
        padding: 0.75rem 1rem;
        border-radius: 8px;
        color: white;
        font-size: 1.5rem;
        font-weight: bold;
        margin: 1.5rem 0 1rem 0;
    }
    
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .stDataFrame {
        border-radius: 10px;
    }
    
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
</style>
""",
    unsafe_allow_html=True,
)


def main():
    # Custom styled header
    st.markdown(
        '<div class="main-header">🚀 Wheel Tracker</div>', unsafe_allow_html=True
    )

    # Sidebar for adding trades
    with st.sidebar:
        st.markdown(
            '<div class="section-header">📝 Add New Trade</div>', unsafe_allow_html=True
        )

        # Trade form
        with st.form("add_trade_form"):
            # Compact layout with columns
            col1, col2 = st.columns(2)

            with col1:
                symbol = st.text_input("Symbol", placeholder="AAPL")
                trade_type = st.selectbox(
                    "Type", ["stock", "put", "call"], help="Trade type"
                )
                quantity = st.number_input("Qty", min_value=1, value=1)

            with col2:
                side = st.selectbox("Side", ["buy", "sell"])
                price = st.number_input("Price", min_value=0.01, value=150.0, step=0.01)
                strategy = st.text_input("Strategy", placeholder="wheel")

                # Option contract details - always show for better UX
            st.markdown("**📋 Contract Details**")

            # Three-column layout for: Date, Type, Strike
            contract_col1, contract_col2, contract_col3 = st.columns(3)

            with contract_col1:
                expiration_date = st.date_input(
                    "Expiration",
                    value=date.today(),
                    help="Option expiration date (e.g., Aug 5, 2025)",
                )

            with contract_col2:
                # Contract type display (not used in logic, just for reference)
                st.selectbox(
                    "Type",
                    ["C", "P"],
                    help="C = Call, P = Put",
                    format_func=lambda x: "Call" if x == "C" else "Put",
                )

            with contract_col3:
                strike_price = st.number_input(
                    "Strike",
                    min_value=0.01,
                    value=150.0,
                    step=0.01,
                    help="Option strike price (e.g., 219)",
                )

            submitted = st.form_submit_button("➕ Add Trade", use_container_width=True)

            if submitted:
                if symbol and price > 0:
                    # Determine option type from contract details
                    is_option = trade_type in ["put", "call"]

                    # Use trade_type for option_type field
                    final_option_type = trade_type if is_option else None

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
                            if is_option
                            else None
                        ),
                        strike_price=strike_price if is_option else None,
                        option_type=final_option_type,
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
    st.markdown(
        '<div class="section-header">📊 Trade History</div>', unsafe_allow_html=True
    )

    # Get all trades
    try:
        trades = db.list_trades()

        if trades:
            # Convert trades to DataFrame for display
            trade_data = []
            for trade in trades:
                # Add color coding for side
                side_display = (
                    f"🟢 {trade.side.upper()}"
                    if trade.side == "buy"
                    else f"🔴 {trade.side.upper()}"
                )

                # Add emoji for trade type
                type_display = {"stock": "📈", "put": "📉", "call": "📈"}.get(
                    trade.option_type or "stock", "📈"
                )

                trade_data.append(
                    {
                        "ID": trade.id,
                        "Symbol": f"💼 {trade.symbol}",
                        "Side": side_display,
                        "Quantity": f"{trade.quantity:,}",
                        "Price": f"${trade.price:.2f}",
                        "Type": f"{type_display} {trade.option_type or 'stock'}",
                        "Strike": (
                            f"${trade.strike_price:.2f}" if trade.strike_price else "-"
                        ),
                        "Expiration": (
                            trade.expiration_date.strftime("%Y-%m-%d")
                            if trade.expiration_date
                            else "-"
                        ),
                        "Strategy": f"🎯 {trade.strategy}" if trade.strategy else "-",
                        "Date": f"📅 {trade.timestamp.strftime('%Y-%m-%d %H:%M')}",
                    }
                )

            df = pd.DataFrame(trade_data)

            # Style the dataframe
            st.markdown(
                """
            <style>
            .stDataFrame {
                border-radius: 15px;
                overflow: hidden;
                box-shadow: 0 8px 16px rgba(0,0,0,0.1);
            }
            </style>
            """,
                unsafe_allow_html=True,
            )

            st.dataframe(df, use_container_width=True, hide_index=True)

            # Cost basis calculations
            st.markdown(
                '<div class="section-header">💰 Cost Basis Analysis</div>',
                unsafe_allow_html=True,
            )

            # Group trades by symbol
            symbols = set(trade.symbol for trade in trades)

            for symbol in sorted(symbols):
                symbol_trades = [trade for trade in trades if trade.symbol == symbol]
                basis = cost_basis(symbol_trades, use_wheel_strategy=True)

                # Create custom metric cards
                st.markdown(f"### 📈 {symbol} Position")

                # Determine colors based on values
                shares_color = "🟢" if basis["shares"] >= 0 else "🔴"
                premium_color = "🟢" if basis["net_premium"] >= 0 else "🔴"
                pnl_color = "🟢" if basis["total_pnl"] >= 0 else "🔴"

                col1, col2, col3, col4, col5 = st.columns(5)

                with col1:
                    st.markdown(
                        f"""
                    <div class="metric-card">
                        <div class="metric-label">📊 Shares</div>
                        <div class="metric-value">{shares_color} {basis['shares']:.0f}</div>
                        <div style="font-size: 0.8rem; opacity: 0.8;">Current position</div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                with col2:
                    st.markdown(
                        f"""
                    <div class="metric-card">
                        <div class="metric-label">💵 Basis (excl. premium)</div>
                        <div class="metric-value">${basis['basis_without_premium']:.2f}</div>
                        <div style="font-size: 0.8rem; opacity: 0.8;">Per share cost</div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                with col3:
                    st.markdown(
                        f"""
                    <div class="metric-card">
                        <div class="metric-label">🎯 Basis (incl. premium)</div>
                        <div class="metric-value">${basis['basis_with_premium']:.2f}</div>
                        <div style="font-size: 0.8rem; opacity: 0.8;">With options</div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                with col4:
                    st.markdown(
                        f"""
                    <div class="metric-card">
                        <div class="metric-label">💎 Net Premium</div>
                        <div class="metric-value">{premium_color} ${basis['net_premium']:.2f}</div>
                        <div style="font-size: 0.8rem; opacity: 0.8;">Option income</div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                with col5:
                    st.markdown(
                        f"""
                    <div class="metric-card">
                        <div class="metric-label">💰 Total PnL</div>
                        <div class="metric-value">{pnl_color} ${basis['total_pnl']:.2f}</div>
                        <div style="font-size: 0.8rem; opacity: 0.8;">Realized + Premium</div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

            # Analytics and Charts
            st.markdown(
                '<div class="section-header">📈 Analytics & Insights</div>',
                unsafe_allow_html=True,
            )

            # Convert trades to DataFrame for analytics
            df = trades_to_dataframe(trades)

            if not df.empty:
                # Monthly Net Premium Chart
                monthly_premium = monthly_net_premium(df)
                if not monthly_premium.empty:
                    st.markdown("### 📊 Monthly Net Premium")

                    # Add some spacing
                    st.markdown("<br>", unsafe_allow_html=True)

                    # Convert to DataFrame for Altair
                    monthly_df = monthly_premium.reset_index()
                    monthly_df.columns = ["month", "premium"]
                    monthly_df["month"] = monthly_df["month"].astype(str)

                    # Enhanced chart styling
                    chart = (
                        alt.Chart(monthly_df)
                        .mark_bar(size=30, cornerRadius=5)
                        .encode(
                            x=alt.X(
                                "month:N", title="Month", axis=alt.Axis(labelAngle=45)
                            ),
                            y=alt.Y("premium:Q", title="Net Premium ($)"),
                            color=alt.condition(
                                alt.datum.premium > 0,
                                alt.value("#00ff88"),
                                alt.value("#ff4444"),
                            ),
                            tooltip=[
                                alt.Tooltip("month:N", title="Month"),
                                alt.Tooltip(
                                    "premium:Q", title="Premium", format="$,.0f"
                                ),
                            ],
                        )
                        .properties(
                            width="container",
                            height=400,
                            title="Monthly Option Premium Performance",
                        )
                        .configure_axis(
                            gridColor="#f0f0f0",
                            domainColor="#666666",
                            titleFontSize=14,
                            labelFontSize=12,
                        )
                        .configure_title(fontSize=18, fontWeight="bold")
                    )

                    st.altair_chart(chart, use_container_width=True)

                # Cumulative Net Premium Chart
                cumulative_df = cumulative_net_premium(df)
                if not cumulative_df.empty:
                    st.markdown("### 📈 Cumulative Net Premium")
                    st.markdown("<br>", unsafe_allow_html=True)

                    # Enhanced line chart
                    chart = (
                        alt.Chart(cumulative_df)
                        .mark_line(strokeWidth=3, stroke="#667eea")
                        .encode(
                            x=alt.X("timestamp:T", title="Date"),
                            y=alt.Y(
                                "cumulative_premium:Q", title="Cumulative Premium ($)"
                            ),
                            tooltip=[
                                alt.Tooltip(
                                    "timestamp:T", title="Date", format="%Y-%m-%d"
                                ),
                                alt.Tooltip(
                                    "cumulative_premium:Q",
                                    title="Cumulative Premium",
                                    format="$,.0f",
                                ),
                            ],
                        )
                        .properties(
                            width="container",
                            height=400,
                            title="Cumulative Option Premium Over Time",
                        )
                        .configure_axis(
                            gridColor="#f0f0f0",
                            domainColor="#666666",
                            titleFontSize=14,
                            labelFontSize=12,
                        )
                        .configure_title(fontSize=18, fontWeight="bold")
                    )

                    st.altair_chart(chart, use_container_width=True)

                # Open Option Obligations Table with Closing Actions
                obligations_df = get_open_option_positions_for_closing(df)
                if not obligations_df.empty:
                    st.markdown("### ⚠️ Open Option Obligations")
                    st.markdown("<br>", unsafe_allow_html=True)

                    # Format the table for display with emojis
                    display_df = obligations_df[
                        [
                            "symbol",
                            "strike_price",
                            "expiration_date",
                            "option_type",
                            "net_quantity",
                        ]
                    ].copy()
                    display_df["symbol"] = display_df["symbol"].apply(
                        lambda x: f"💼 {x}"
                    )
                    display_df["strike_price"] = display_df["strike_price"].apply(
                        lambda x: f"${x:.2f}"
                    )
                    display_df["expiration_date"] = display_df[
                        "expiration_date"
                    ].dt.strftime("%Y-%m-%d")
                    display_df["net_quantity"] = display_df["net_quantity"].apply(
                        lambda x: f"{'🟢' if x > 0 else '🔴'} {x:+.0f}"
                    )
                    display_df["option_type"] = display_df["option_type"].apply(
                        lambda x: f"{'📈' if x == 'call' else '📉'} {x.upper()}"
                    )

                    # Rename columns for display
                    display_df.columns = [
                        "Symbol",
                        "Strike",
                        "Expiration",
                        "Type",
                        "Net Quantity",
                    ]

                    # Style the obligations table
                    st.markdown(
                        """
                    <style>
                    .obligations-table {
                        border-radius: 15px;
                        overflow: hidden;
                        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    }
                    </style>
                    """,
                        unsafe_allow_html=True,
                    )

                    st.dataframe(display_df, use_container_width=True, hide_index=True)

                    # Add closing functionality
                    st.markdown("### 🔄 Close Positions")

                    # Create a form for closing positions
                    with st.form("close_position_form"):
                        # Position selector
                        position_options = []
                        for idx, row in obligations_df.iterrows():
                            symbol = row["symbol"]
                            strike = row["strike_price"]
                            exp = row["expiration_date"].strftime("%Y-%m-%d")
                            opt_type = row["option_type"].upper()
                            qty = abs(row["net_quantity"])
                            side = "SHORT" if row["net_quantity"] < 0 else "LONG"

                            position_options.append(
                                f"{symbol} {strike} {opt_type} {exp} ({qty} {side})"
                            )

                        selected_position = st.selectbox(
                            "Select Position to Close",
                            position_options,
                            help="Choose the option position to close",
                        )

                        # Get the selected position data
                        selected_idx = position_options.index(selected_position)
                        selected_row = obligations_df.iloc[selected_idx]

                        # Action type selector
                        action_options = []
                        if selected_row["can_buy_to_close"]:
                            action_options.append("Buy to Close")
                        if selected_row["can_sell_to_close"]:
                            action_options.append("Sell to Close")
                        if selected_row["can_exercise"]:
                            action_options.append("Exercise (Assignment)")

                        action_type = st.selectbox(
                            "Action", action_options, help="How to close this position"
                        )

                        # Price input (only for buy/sell to close)
                        if "Close" in action_type:
                            close_price = st.number_input(
                                "Close Price",
                                min_value=0.0,
                                value=0.50,
                                step=0.01,
                                help="Price to close the position (can be 0 for assignments)",
                            )
                        else:
                            close_price = selected_row[
                                "strike_price"
                            ]  # Use strike for assignment

                        close_submitted = st.form_submit_button("🔄 Close Position")

                        if close_submitted:
                            try:
                                # Create the closing trade
                                if "Buy to Close" in action_type:
                                    # Buy to close a short position
                                    trade_to_insert = Trade(
                                        symbol=selected_row["symbol"].upper(),
                                        quantity=selected_row["abs_quantity"],
                                        price=close_price,
                                        side="buy",
                                        timestamp=datetime.now(),
                                        strategy="close",
                                        expiration_date=selected_row["expiration_date"],
                                        strike_price=selected_row["strike_price"],
                                        option_type=selected_row["option_type"],
                                    )

                                    # Insert the closing trade
                                    inserted_trade = db.insert_trade(trade_to_insert)
                                    st.success(
                                        f"Position closed: {action_type} - {inserted_trade.symbol} {inserted_trade.side} {inserted_trade.quantity}"
                                    )
                                    st.rerun()  # Refresh the page to show updated positions
                                elif "Sell to Close" in action_type:
                                    # Sell to close a long position
                                    trade_to_insert = Trade(
                                        symbol=selected_row["symbol"].upper(),
                                        quantity=selected_row["abs_quantity"],
                                        price=close_price,
                                        side="sell",
                                        timestamp=datetime.now(),
                                        strategy="close",
                                        expiration_date=selected_row["expiration_date"],
                                        strike_price=selected_row["strike_price"],
                                        option_type=selected_row["option_type"],
                                    )

                                    # Insert the closing trade
                                    inserted_trade = db.insert_trade(trade_to_insert)
                                    st.success(
                                        f"Position closed: {action_type} - {inserted_trade.symbol} {inserted_trade.side} {inserted_trade.quantity}"
                                    )
                                    st.rerun()  # Refresh the page to show updated positions
                                elif "Exercise" in action_type:
                                    # Assignment - create TWO trades:
                                    # 1. Stock trade (buying/selling shares at strike price)
                                    # 2. Option trade (closing out the option position)

                                    # Stock trade
                                    stock_trade = Trade(
                                        symbol=selected_row["symbol"].upper(),
                                        quantity=selected_row["abs_quantity"]
                                        * 100,  # 100 shares per contract
                                        price=selected_row["strike_price"],
                                        side=(
                                            "buy"
                                            if selected_row["option_type"] == "put"
                                            else "sell"
                                        ),
                                        timestamp=datetime.now(),
                                        strategy="assignment",
                                        expiration_date=None,
                                        strike_price=None,
                                        option_type=None,
                                    )

                                    # Option closing trade
                                    option_trade = Trade(
                                        symbol=selected_row["symbol"].upper(),
                                        quantity=selected_row["abs_quantity"],
                                        price=0.0,  # Zero price for assignment
                                        side=(
                                            "buy"
                                            if selected_row["net_quantity"] < 0
                                            else "sell"
                                        ),
                                        timestamp=datetime.now(),
                                        strategy="assignment",
                                        expiration_date=selected_row["expiration_date"],
                                        strike_price=selected_row["strike_price"],
                                        option_type=selected_row["option_type"],
                                    )

                                    # Insert both trades
                                    inserted_stock = db.insert_trade(stock_trade)
                                    db.insert_trade(
                                        option_trade
                                    )  # Close the option position

                                    st.success(
                                        f"Position exercised: {inserted_stock.symbol} {inserted_stock.side} {inserted_stock.quantity} shares + option closed"
                                    )
                                    st.rerun()  # Refresh the page to show updated positions

                            except Exception as e:
                                st.error(f"Error closing position: {e}")
                else:
                    st.markdown(
                        """
                    <div style="background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%); 
                                padding: 1rem; border-radius: 10px; color: white; text-align: center;">
                        <h4>🎉 No Open Option Obligations</h4>
                        <p>All your option positions are closed!</p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    """
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            padding: 1rem; border-radius: 10px; color: white; text-align: center;">
                    <h4>📊 No Trades Available</h4>
                    <p>Add some trades to see analytics!</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

        else:
            st.markdown(
                """
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 2rem; border-radius: 15px; color: white; text-align: center; margin: 2rem 0;">
                <h3>🚀 Welcome to Wheel Tracker!</h3>
                <p style="font-size: 1.1rem; margin: 1rem 0;">Add your first trade using the sidebar to get started.</p>
                <p style="opacity: 0.8;">Track your option strategies and analyze your performance.</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

    except Exception as e:
        st.markdown(
            f"""
        <div style="background: linear-gradient(135deg, #ff4444 0%, #cc0000 100%); 
                    padding: 1rem; border-radius: 10px; color: white; text-align: center;">
            <h4>❌ Error Loading Trades</h4>
            <p>{e}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
