import streamlit as st
import pandas as pd
from datetime import datetime, date
from wheeltracker.db import db
from wheeltracker.models import Trade
from wheeltracker.calculations import cost_basis


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
                "Trade Type",
                ["stock", "put", "call"],
                help="Select the type of trade"
            )
            
            side = st.selectbox("Side", ["buy", "sell"])
            quantity = st.number_input("Quantity", min_value=1, value=1)
            price = st.number_input("Price", min_value=0.01, value=150.0, step=0.01)
            
            # Option-specific fields
            expiration_date = None
            strike_price = None
            option_type = None
            
            if trade_type in ["put", "call"]:
                option_type = trade_type
                expiration_date = st.date_input(
                    "Expiration Date",
                    value=date.today(),
                    help="Option expiration date"
                )
                strike_price = st.number_input(
                    "Strike Price",
                    min_value=0.01,
                    value=150.0,
                    step=0.01,
                    help="Option strike price"
                )
            
            strategy = st.text_input("Strategy", placeholder="wheel", help="Trading strategy name")
            
            submitted = st.form_submit_button("Add Trade")
            
            if submitted:
                if symbol and price > 0:
                    # Create trade object
                    trade = Trade(
                        symbol=symbol.upper(),
                        quantity=quantity,
                        price=price,
                        side=side,
                        timestamp=datetime.now(),
                        strategy=strategy if strategy else None,
                        expiration_date=datetime.combine(expiration_date, datetime.min.time()) if expiration_date else None,
                        strike_price=strike_price,
                        option_type=option_type
                    )
                    
                    # Insert trade
                    try:
                        inserted_trade = db.insert_trade(trade)
                        st.success(f"Trade added: {inserted_trade.symbol} {inserted_trade.side} {inserted_trade.quantity}")
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
                trade_data.append({
                    "ID": trade.id,
                    "Symbol": trade.symbol,
                    "Side": trade.side,
                    "Quantity": trade.quantity,
                    "Price": f"${trade.price:.2f}",
                    "Type": trade.option_type or "stock",
                    "Strike": f"${trade.strike_price:.2f}" if trade.strike_price else "-",
                    "Expiration": trade.expiration_date.strftime("%Y-%m-%d") if trade.expiration_date else "-",
                    "Strategy": trade.strategy or "-",
                    "Date": trade.timestamp.strftime("%Y-%m-%d %H:%M")
                })
            
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
                        help="Current share position (positive = long, negative = short)"
                    )
                
                with col2:
                    st.metric(
                        "Basis (excl. premium)",
                        f"${basis['basis_without_premium']:.2f}",
                        help="Cost basis per share excluding option premiums"
                    )
                
                with col3:
                    st.metric(
                        "Basis (incl. premium)",
                        f"${basis['basis_with_premium']:.2f}",
                        help="Cost basis per share including option premiums"
                    )
                
                with col4:
                    st.metric(
                        "Net Premium",
                        f"${basis['net_premium']:.2f}",
                        help="Total option premiums received/paid"
                    )
        
        else:
            st.info("No trades found. Add your first trade using the sidebar!")
            
    except Exception as e:
        st.error(f"Error loading trades: {e}")


if __name__ == "__main__":
    main() 