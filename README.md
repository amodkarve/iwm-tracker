# IWM Put Selling Strategy Tracker

A comprehensive tracking and analysis system for an IWM (Russell 2000 ETF) put selling strategy targeting 18-20% annual returns.

## 🎯 Strategy Overview

This system tracks a modified wheel strategy on IWM with the following approach:
- **Target**: 18-20% annual return purely from put selling
- **Primary Strategy**: Sell 1 DTE puts near the money, targeting 0.08% daily premium ($800/day on $1M account)
- **Position Sizing**: 5-10 contracts per trade ($600-800 daily premium target)
- **Exit**: Close positions at $0.05 per contract
- **Rolling**: Roll ITM puts if can collect 0.05-0.08% additional premium
- **Assignment Handling**: Sell covered calls above cost basis + simultaneous puts
- **DITM Conversion**: Convert shares to DITM calls (90 DTE) to free up buying power
- **Hedging**: Buy 30 DTE, 5% OTM puts (~$1.50/contract) when market is overheated

## ✨ Features

### Core Tracking
- ✅ Trade entry and management (stocks, puts, calls)
- ✅ Cost basis calculations with wheel strategy accounting
- ✅ Premium tracking (monthly & cumulative)
- ✅ Open position management
- ✅ Position closing (buy to close, sell to close, assignment)

### New Features
- 🆕 **Real-time Market Data**: IWM price data via yfinance (15-20 min delay)
- 🆕 **Technical Indicators**:
  - Ehler's Instantaneous Trendline (trend detection)
  - Cycle Swing Momentum (overbought/oversold)
- 🆕 **Performance Tracking**:
  - Annualized return calculation
  - Progress toward 18-20% goal
  - Win rate and average win/loss
  - Sharpe ratio and max drawdown
- 🆕 **Position Sizing Recommendations**: Automatic contract sizing based on premium targets
- 🆕 **Strategy Analytics**: Premium calculations aligned with 0.08% daily target

## 📦 Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

1. **Clone or navigate to the repository**:
```bash
cd /Users/amod/antigravity/iwm-tracker
```

2. **Create a virtual environment** (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

## 🚀 Usage

### Running the Application

**Enhanced version** (with indicators and performance tracking):
```bash
streamlit run app_enhanced.py
```

**Original version** (basic tracking):
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

### Adding Trades

Use the sidebar form to add trades:
1. Enter symbol (default: IWM)
2. Select type (stock/put/call)
3. Enter quantity, price, and side (buy/sell)
4. For options: add expiration date and strike price
5. Click "Add Trade"

### Viewing Performance

The enhanced app displays:
- **Market Data**: Current IWM price (delayed)
- **Indicators**: Ehler's Trend and Cycle Swing signals
- **Performance Metrics**: Annualized return, total premium, win rate
- **Position Sizing**: Recommended contracts for target premium
- **Trade History**: All trades with cost basis analysis
- **Analytics**: Monthly premium charts, cumulative performance

## 📊 Technical Indicators

### Ehler's Instantaneous Trendline
- **Purpose**: Identify market trend direction
- **Signals**: Bullish (↑), Bearish (↓), Neutral (→)
- **Use**: Prefer selling puts in bullish trends

### Cycle Swing Momentum
- **Purpose**: Detect overbought/oversold conditions
- **Signals**: Overbought, Oversold, Neutral
- **Use**: Avoid selling puts when oversold, consider hedges when overbought

## 🧪 Testing

Run unit tests:
```bash
# Test premium calculator
python3 tests/unit/test_premium_calculator.py

# Run all tests (when pytest is configured)
pytest tests/unit/ -v
```

## 📁 Project Structure

```
iwm-tracker/
├── app.py                          # Original Streamlit app
├── app_enhanced.py                 # Enhanced app with indicators
├── requirements.txt                # Python dependencies
├── wheel.db                        # SQLite database
├── src/
│   ├── wheeltracker/              # Core tracking modules
│   │   ├── db.py                  # Database operations
│   │   ├── models.py              # Data models
│   │   ├── calculations.py        # Cost basis calculations
│   │   └── analytics.py           # Trade analytics
│   ├── market_data/               # Market data fetching
│   │   ├── __init__.py
│   │   └── price_fetcher.py       # yfinance integration
│   ├── indicators/                # Technical indicators
│   │   ├── __init__.py
│   │   ├── ehlers_trend.py        # Ehler's Instantaneous Trend
│   │   └── cycle_swing.py         # Cycle Swing Momentum
│   ├── strategy/                  # Strategy logic
│   │   ├── __init__.py
│   │   ├── rules.py               # Strategy constants
│   │   └── premium_calculator.py  # Premium calculations
│   └── analytics/                 # Performance analytics
│       ├── __init__.py
│       └── performance.py         # Performance metrics
├── tests/
│   ├── unit/                      # Unit tests
│   │   └── test_premium_calculator.py
│   └── integration/               # Integration tests
└── pinescript/                    # Original indicator code
    ├── instantaneous_trend.pinescript
    └── cycle_swing.pinescript
```

## 🔧 Configuration

### Account Settings
Edit `src/strategy/rules.py` to customize:
- `DEFAULT_ACCOUNT_SIZE`: Your account size (default: $1M)
- `TARGET_DAILY_PREMIUM_PCT`: Daily premium target (default: 0.08%)
- `MIN_CONTRACTS` / `MAX_CONTRACTS`: Position size limits
- `CLOSE_THRESHOLD`: Exit price for options
- `ROLL_PREMIUM_MIN` / `MAX`: Roll premium targets

### Market Data
Currently using yfinance (free, 15-20 min delay). To upgrade to real-time data:
1. Sign up for Tradier Brokerage ($10/month)
2. Update `src/market_data/price_fetcher.py` with Tradier API
3. Add API credentials to `.env` file

## 📈 Performance Goals

- **Target Annual Return**: 18-20%
- **Daily Premium Target**: $600-800 (0.08% of $1M account)
- **Strategy**: Consistent premium collection through disciplined put selling
- **Risk Management**: Position sizing, rolling, hedging, and DITM conversions

## 🚧 Roadmap

### Phase 1: Core Features ✅
- [x] Market data integration (yfinance)
- [x] Technical indicators (Ehler's, Cycle Swing)
- [x] Performance tracking
- [x] Position sizing calculator

### Phase 2: Enhanced Features (Future)
- [ ] Real-time data integration (Tradier API)
- [ ] Trade suggestion engine
- [ ] Automated roll detection
- [ ] DITM conversion suggestions
- [ ] Hedge timing recommendations

### Phase 3: Deployment (Future)
- [ ] Docker containerization
- [ ] FastAPI backend
- [ ] React frontend
- [ ] VPS deployment

## 📝 License

Private project for personal use.

## 🤝 Contributing

This is a personal trading system. Not accepting external contributions.

## ⚠️ Disclaimer

This software is for educational and personal use only. Trading options involves substantial risk. Past performance does not guarantee future results. Always do your own research and consult with a financial advisor before making investment decisions.
 