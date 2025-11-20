"""
Enhanced IWM Put Selling Strategy Tracker

Features:
- Real-time IWM price data (yfinance)
- Technical indicators (Ehler's Trend, Cycle Swing Momentum)
- Performance tracking (18-20% annual goal)
- Premium calculations and position sizing
- Trade history and analytics
"""
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

# Import new modules
from market_data import get_iwm_price, get_price_series, get_hl2_series, get_data_source
from indicators import calculate_instantaneous_trend, calculate_cycle_swing
from strategy import calculate_daily_target, get_position_sizing_recommendation, get_trade_recommendations
from analytics.performance import get_performance_summary


# Configure page
st.set_page_config(
    page_title="IWM Strategy Tracker",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
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
    
    .indicator-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    
    .bullish {
        background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
    }
    
    .bearish {
        background: linear-gradient(135deg, #ff4444 0%, #cc0000 100%);
    }
    
    .neutral {
        background: linear-gradient(135deg, #888888 0%, #666666 100%);
    }
</style>
""",
    unsafe_allow_html=True,
)


def main():
    """Main application"""
    
    # Database selector in header
    st.markdown("### 🎯 IWM Put Selling Strategy Tracker")
    
    # Create header columns for database selector
    header_col1, header_col2, header_col3 = st.columns([2, 1, 1])
    
    with header_col2:
        # Get available database files
        import glob
        db_files = glob.glob("*.db")
        if not db_files:
            db_files = ["wheel.db", "wheel_test.db"]
        
        # Get current database from session state or environment
        if 'current_db' not in st.session_state:
            st.session_state.current_db = os.getenv('WHEEL_DB_PATH', 'wheel.db')
        
        # Database selector
        selected_db = st.selectbox(
            "📊 Database",
            options=db_files,
            index=db_files.index(st.session_state.current_db) if st.session_state.current_db in db_files else 0,
            help="Switch between test and production databases"
        )
        
        # If database changed, reconnect
        if selected_db != st.session_state.current_db:
            st.session_state.current_db = selected_db
            # Reinitialize database connection
            from wheeltracker.db import Database
            global db
            db = Database(selected_db)
            st.success(f"✅ Switched to {selected_db}")
            st.rerun()
    
    with header_col3:
        # Show database info
        db_size = os.path.getsize(st.session_state.current_db) if os.path.exists(st.session_state.current_db) else 0
        db_type = "🟢 PROD" if "test" not in st.session_state.current_db.lower() else "🟡 TEST"
        st.metric(
            label="DB Status",
            value=db_type,
            delta=f"{db_size/1024:.1f} KB"
        )
    
    st.markdown("---")
    
    # Sidebar for adding trades
    with st.sidebar:
        st.markdown("### 📝 Add New Trade")

        with st.form("add_trade_form"):
            col1, col2 = st.columns(2)

            with col1:
                symbol = st.text_input("Symbol", value="IWM")
                trade_type = st.selectbox("Type", ["stock", "put", "call"])
                quantity = st.number_input("Qty", min_value=1, value=1)

            with col2:
                side = st.selectbox("Side", ["buy", "sell"])
                price = st.number_input("Price", min_value=0.01, value=0.80, step=0.01)
                strategy = st.text_input("Strategy", value="wheel")

            st.markdown("**📋 Contract Details**")
            contract_col1, contract_col2, contract_col3 = st.columns(3)

            with contract_col1:
                expiration_date = st.date_input("Expiration", value=date.today())

            with contract_col2:
                st.selectbox(
                    "Type",
                    ["C", "P"],
                    help="C = Call, P = Put",
                    format_func=lambda x: "Call" if x == "C" else "Put",
                )

            with contract_col3:
                strike_price = st.number_input("Strike", min_value=0.01, value=200.0, step=0.01)

            submitted = st.form_submit_button("➕ Add Trade", use_container_width=True)

            if submitted:
                if symbol and price > 0:
                    is_option = trade_type in ["put", "call"]
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
                        option_type=trade_type if is_option else None,
                    )

                    try:
                        inserted_trade = db.insert_trade(trade)
                        st.success(f"✅ Trade added: {inserted_trade.symbol}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
                else:
                    st.error("Please fill in all required fields")

    # Main content
    # Market Data & Indicators Section
    st.markdown("## 📊 Market Data & Indicators")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.spinner("Fetching IWM price..."):
            iwm_price = get_iwm_price()
            if iwm_price:
                st.markdown(
                    f"""
                <div class="metric-card">
                    <div class="metric-label">IWM Current Price</div>
                    <div class="metric-value">${iwm_price:.2f}</div>
                    <div style="font-size: 0.8rem; opacity: 0.8;">15-20 min delay</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                st.warning("Unable to fetch IWM price")
    
    with col2:
        with st.spinner("Calculating Ehler's Trend..."):
            hl2_series = get_hl2_series(period="3mo")
            if not hl2_series.empty:
                trend_result = calculate_instantaneous_trend(hl2_series)
                trend_signal = int(trend_result['signal'].iloc[-1]) if not trend_result['signal'].empty else 0
                
                signal_class = "bullish" if trend_signal > 0 else "bearish" if trend_signal < 0 else "neutral"
                signal_text = "BULLISH ↑" if trend_signal > 0 else "BEARISH ↓" if trend_signal < 0 else "NEUTRAL →"
                
                st.markdown(
                    f"""
                <div class="indicator-card {signal_class}">
                    <div class="metric-label">Ehler's Trend</div>
                    <div class="metric-value">{signal_text}</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                st.warning("Unable to calculate trend")
    
    with col3:
        with st.spinner("Calculating Cycle Swing..."):
            price_series = get_price_series(period="3mo")
            if not price_series.empty:
                csi_result = calculate_cycle_swing(price_series)
                csi_signal = int(csi_result['signal'].iloc[-1]) if not csi_result['signal'].empty else 0
                
                signal_class = "bullish" if csi_signal > 0 else "bearish" if csi_signal < 0 else "neutral"
                signal_text = "OVERBOUGHT" if csi_signal > 0 else "OVERSOLD" if csi_signal < 0 else "NEUTRAL"
                
                st.markdown(
                    f"""
                <div class="indicator-card {signal_class}">
                    <div class="metric-label">Cycle Swing Momentum</div>
                    <div class="metric-value">{signal_text}</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                st.warning("Unable to calculate momentum")

    # Trade Recommendations Section
    st.markdown("## 💡 Trade Recommendations")
    
    st.markdown("### 🎯 Suggested 1 DTE Puts to Sell")
    
    with st.spinner("Analyzing market and generating recommendations..."):
        try:
            recommendations = get_trade_recommendations(account_value=1_000_000, max_recommendations=3)
            
            if recommendations:
                data_source = get_data_source()
                if data_source == 'marketdata':
                    st.success("✅ Using real-time Market Data App for recommendations")
                else:
                    st.warning("⚠️ Using estimated data (Market Data App not configured)")
                
                for i, rec in enumerate(recommendations, 1):
                    # Confidence badge
                    confidence_colors = {
                        'high': '🟢',
                        'medium': '🟡',
                        'low': '🔴'
                    }
                    confidence_badge = confidence_colors.get(rec.confidence, '⚪')
                    
                    with st.expander(f"{confidence_badge} **Recommendation #{i}** - Strike ${rec.strike:.2f} ({rec.confidence.upper()} confidence)", expanded=(i==1)):
                        # Display recommendation details
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Strike Price", f"${rec.strike:.2f}")
                            st.metric("Bid/Ask", f"${rec.bid:.2f} / ${rec.ask:.2f}")
                            st.metric("Mid Price", f"${rec.mid:.2f}")
                        
                        with col2:
                            st.metric("Recommended Contracts", rec.recommended_contracts)
                            st.metric("Expected Premium", f"${rec.expected_premium:.0f}")
                            st.metric("% of Account", f"{rec.premium_pct*100:.3f}%")
                        
                        with col3:
                            if rec.delta is not None:
                                st.metric("Delta", f"{rec.delta:.3f}")
                            if rec.iv is not None:
                                st.metric("IV", f"{rec.iv*100:.1f}%")
                            if rec.volume is not None:
                                st.metric("Volume", f"{rec.volume:,}")
                        
                        # Reasoning
                        st.info(f"**Analysis:** {rec.reason}")
                        
                        # Quick Entry Form
                        st.markdown("#### 🚀 Quick Entry")
                        
                        with st.form(f"quick_entry_{i}"):
                            qe_col1, qe_col2, qe_col3 = st.columns(3)
                            
                            with qe_col1:
                                qe_contracts = st.number_input(
                                    "Contracts",
                                    min_value=1,
                                    max_value=20,
                                    value=rec.recommended_contracts,
                                    key=f"qe_contracts_{i}"
                                )
                            
                            with qe_col2:
                                qe_price = st.number_input(
                                    "Fill Price",
                                    min_value=0.01,
                                    value=float(rec.recommended_price),
                                    step=0.01,
                                    key=f"qe_price_{i}",
                                    help="Adjust based on your actual fill"
                                )
                            
                            with qe_col3:
                                qe_strategy = st.text_input(
                                    "Strategy",
                                    value="wheel",
                                    key=f"qe_strategy_{i}"
                                )
                            
                            # Calculate expected premium with user's inputs
                            user_premium = qe_price * qe_contracts * 100
                            st.caption(f"💰 Expected Premium: ${user_premium:.2f}")
                            
                            # IMPORTANT: Button label must be static, otherwise Streamlit thinks it's a new button
                            # when the price changes and won't trigger the form submission
                            qe_submit = st.form_submit_button(
                                "✅ Enter Trade",
                                use_container_width=True
                            )
                            
                            if qe_submit:
                                st.write("🔍 Debug: Form submitted!")  # Debug message
                                try:
                                    # Convert expiration date properly
                                    # rec.expiration is a date object, need to convert to datetime
                                    if isinstance(rec.expiration, date) and not isinstance(rec.expiration, datetime):
                                        expiration_dt = datetime.combine(rec.expiration, datetime.min.time())
                                    else:
                                        expiration_dt = rec.expiration
                                    
                                    # Create and insert trade
                                    trade = Trade(
                                        symbol=rec.symbol,
                                        quantity=qe_contracts,
                                        price=qe_price,
                                        side="sell",
                                        timestamp=datetime.now(),
                                        strategy=qe_strategy,
                                        expiration_date=expiration_dt,
                                        strike_price=rec.strike,
                                        option_type=rec.option_type
                                    )
                                    
                                    st.write(f"🔍 Debug: Trade object created: {trade.symbol} {trade.quantity}x @ ${trade.price}")  # Debug
                                    st.write(f"🔍 Debug: Expiration: {trade.expiration_date}")  # Debug
                                    
                                    inserted_trade = db.insert_trade(trade)
                                    
                                    st.write(f"🔍 Debug: Trade inserted with ID: {inserted_trade.id}")  # Debug
                                    
                                    st.success(f"🎉 Trade entered! Sold {qe_contracts} {rec.symbol} ${rec.strike:.2f} puts @ ${qe_price:.2f}")
                                    st.balloons()
                                    
                                    st.write("🔍 Debug: About to rerun...")  # Debug
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"❌ Error entering trade: {e}")
                                    import traceback
                                    st.code(traceback.format_exc())

            
            else:
                st.warning("No recommendations available. Check market data connection.")
        
        except Exception as e:
            st.error(f"Error generating recommendations: {e}")
            import traceback
            st.code(traceback.format_exc())

    # Performance Metrics Section
    st.markdown("## 🎯 Performance Tracking")
    
    trades = db.list_trades()
    
    if trades:
        # Calculate performance
        account_value = 1_000_000  # TODO: Make this configurable
        initial_value = 1_000_000
        
        perf = get_performance_summary(trades, account_value, initial_value)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            annual_return_pct = perf.get('annualized_return', 0) * 100
            color = "🟢" if perf.get('on_track', False) else "🔴"
            st.markdown(
                f"""
            <div class="metric-card">
                <div class="metric-label">Annualized Return</div>
                <div class="metric-value">{color} {annual_return_pct:.2f}%</div>
                <div style="font-size: 0.8rem; opacity: 0.8;">Target: 18-20%</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        
        with col2:
            total_premium = perf.get('total_premium', 0)
            st.markdown(
                f"""
            <div class="metric-card">
                <div class="metric-label">Total Premium</div>
                <div class="metric-value">${total_premium:,.0f}</div>
                <div style="font-size: 0.8rem; opacity: 0.8;">All time</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        
        with col3:
            win_rate = perf.get('win_rate', 0) * 100
            st.markdown(
                f"""
            <div class="metric-card">
                <div class="metric-label">Win Rate</div>
                <div class="metric-value">{win_rate:.1f}%</div>
                <div style="font-size: 0.8rem; opacity: 0.8;">{perf.get('total_trades', 0)} closed trades</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        
        with col4:
            avg_win = perf.get('avg_win', 0)
            st.markdown(
                f"""
            <div class="metric-card">
                <div class="metric-label">Avg Win</div>
                <div class="metric-value">${avg_win:.0f}</div>
                <div style="font-size: 0.8rem; opacity: 0.8;">Per trade</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        
        with col5:
            days_active = perf.get('days_active', 0)
            st.markdown(
                f"""
            <div class="metric-card">
                <div class="metric-label">Days Active</div>
                <div class="metric-value">{days_active}</div>
                <div style="font-size: 0.8rem; opacity: 0.8;">Trading days</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # Position Sizing Recommendation
        st.markdown("## 💡 Position Sizing Recommendation")
        
        if iwm_price:
            # Example: suggest position size for selling puts at current price
            example_option_price = 0.80  # User can adjust this
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                option_price_input = st.number_input(
                    "Option Price (per share)",
                    min_value=0.01,
                    value=example_option_price,
                    step=0.01,
                    help="Enter the option price you're considering"
                )
            
            with col2:
                sizing = get_position_sizing_recommendation(option_price_input, account_value)
                
                st.info(
                    f"""
                    **Recommendation for ${option_price_input:.2f} option:**
                    - 🎯 Daily Target: ${sizing['target_premium']:.0f}
                    - 📊 Contracts: {sizing['contracts']}
                    - 💰 Expected Premium: ${sizing['expected_premium']:.0f}
                    - 📈 % of Account: {sizing['premium_pct']*100:.3f}%
                    """
                )

        # Trade History (existing code)
        st.markdown("## 📋 Trade History")
        
        trade_data = []
        for trade in trades:
            side_display = f"🟢 {trade.side.upper()}" if trade.side == "buy" else f"🔴 {trade.side.upper()}"
            type_display = {"stock": "📈", "put": "📉", "call": "📈"}.get(trade.option_type or "stock", "📈")
            
            trade_data.append({
                "ID": trade.id,
                "Symbol": f"💼 {trade.symbol}",
                "Side": side_display,
                "Quantity": f"{trade.quantity:,}",
                "Price": f"${trade.price:.2f}",
                "Type": f"{type_display} {trade.option_type or 'stock'}",
                "Strike": f"${trade.strike_price:.2f}" if trade.strike_price else "-",
                "Expiration": trade.expiration_date.strftime("%Y-%m-%d") if trade.expiration_date else "-",
                "Strategy": f"🎯 {trade.strategy}" if trade.strategy else "-",
                "Date": f"📅 {trade.timestamp.strftime('%Y-%m-%d %H:%M')}",
            })
        
        df = pd.DataFrame(trade_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Cost Basis Analysis (existing code)
        st.markdown("## 💰 Cost Basis Analysis")
        
        symbols = set(trade.symbol for trade in trades)
        
        for symbol in sorted(symbols):
            symbol_trades = [trade for trade in trades if trade.symbol == symbol]
            basis = cost_basis(symbol_trades, use_wheel_strategy=True)
            
            st.markdown(f"### 📈 {symbol} Position")
            
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
                </div>
                """,
                    unsafe_allow_html=True,
                )

        # Analytics and Charts (existing code continues...)
        st.markdown("## 📈 Analytics & Insights")
        
        df = trades_to_dataframe(trades)
        
        if not df.empty:
            monthly_premium = monthly_net_premium(df)
            if not monthly_premium.empty:
                st.markdown("### 📊 Monthly Net Premium")
                
                monthly_df = monthly_premium.reset_index()
                monthly_df.columns = ["month", "premium"]
                monthly_df["month"] = monthly_df["month"].astype(str)
                
                chart = (
                    alt.Chart(monthly_df)
                    .mark_bar(size=30, cornerRadius=5)
                    .encode(
                        x=alt.X("month:N", title="Month", axis=alt.Axis(labelAngle=45)),
                        y=alt.Y("premium:Q", title="Net Premium ($)"),
                        color=alt.condition(
                            alt.datum.premium > 0,
                            alt.value("#00ff88"),
                            alt.value("#ff4444"),
                        ),
                        tooltip=[
                            alt.Tooltip("month:N", title="Month"),
                            alt.Tooltip("premium:Q", title="Premium", format="$,.0f"),
                        ],
                    )
                    .properties(width="container", height=400)
                )
                
                st.altair_chart(chart, use_container_width=True)
            
            cumulative_df = cumulative_net_premium(df)
            if not cumulative_df.empty:
                st.markdown("### 📈 Cumulative Net Premium")
                
                chart = (
                    alt.Chart(cumulative_df)
                    .mark_line(strokeWidth=3, stroke="#667eea")
                    .encode(
                        x=alt.X("timestamp:T", title="Date"),
                        y=alt.Y("cumulative_premium:Q", title="Cumulative Premium ($)"),
                        tooltip=[
                            alt.Tooltip("timestamp:T", title="Date", format="%Y-%m-%d"),
                            alt.Tooltip("cumulative_premium:Q", title="Cumulative Premium", format="$,.0f"),
                        ],
                    )
                    .properties(width="container", height=400)
                )
                
                st.altair_chart(chart, use_container_width=True)
            
            # Open positions (existing code)
            obligations_df = get_open_option_positions_for_closing(df)
            if not obligations_df.empty:
                st.markdown("### ⚠️ Open Option Obligations")
                
                display_df = obligations_df[
                    ["symbol", "strike_price", "expiration_date", "option_type", "net_quantity"]
                ].copy()
                display_df["symbol"] = display_df["symbol"].apply(lambda x: f"💼 {x}")
                display_df["strike_price"] = display_df["strike_price"].apply(lambda x: f"${x:.2f}")
                display_df["expiration_date"] = display_df["expiration_date"].dt.strftime("%Y-%m-%d")
                display_df["net_quantity"] = display_df["net_quantity"].apply(
                    lambda x: f"{'🟢' if x > 0 else '🔴'} {x:+.0f}"
                )
                display_df["option_type"] = display_df["option_type"].apply(
                    lambda x: f"{'📈' if x == 'call' else '📉'} {x.upper()}"
                )
                
                display_df.columns = ["Symbol", "Strike", "Expiration", "Type", "Net Quantity"]
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.success("🎉 No Open Option Obligations - All positions are closed!")
    
    else:
        st.info("👋 Welcome! Add your first trade using the sidebar to get started.")


if __name__ == "__main__":
    main()
