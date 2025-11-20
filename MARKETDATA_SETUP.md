# Market Data App Integration Guide

## Overview

The IWM Tracker now supports **Market Data App** for real-time stock quotes and options data. This is optional - the system works with free yfinance data by default.

## Why Market Data App?

**Trader Plan ($75/month)** includes:
- ✅ **Real-time stock quotes** (no delay)
- ✅ **Real-time options chains** with Greeks (Delta, Gamma, Theta, Vega, Rho)
- ✅ **Implied Volatility** (IV) data
- ✅ **Unlimited historical data**
- ✅ **High rate limits** (suitable for active trading)

Perfect for your 1 DTE put selling strategy!

## Setup Instructions

### 1. Sign Up for Market Data App

1. Go to https://dashboard.marketdata.app/marketdata/signup
2. Create an account
3. Choose the **Trader plan** ($75/month)

### 2. Get Your API Token

1. Log in to https://dashboard.marketdata.app/
2. Navigate to **API Tokens**
3. Copy your API token

### 3. Configure the IWM Tracker

**Option A: Using Environment Variable (Recommended)**

```bash
# Create .env file
cp .env.example .env

# Edit .env and add your token
MARKETDATA_API_TOKEN=your_token_here
```

**Option B: Using Docker Environment**

Edit `docker-compose.yml` and add:

```yaml
environment:
  - MARKETDATA_API_TOKEN=your_token_here
  - PYTHONUNBUFFERED=1
  - ACCOUNT_SIZE=1000000
```

### 4. Restart the App

```bash
docker-compose down
docker-compose up --build -d
```

## Features Available with Market Data App

### 1. Real-Time IWM Price

The app will automatically use Market Data App for real-time prices instead of delayed yfinance data.

### 2. Options Chain Data

Get 1 DTE puts near the money for your strategy:

```python
from market_data import get_1dte_puts_near_money

# Get 1 DTE puts
puts = get_1dte_puts_near_money()

# Shows: strike, bid, ask, mid, volume, open_interest, IV, Greeks
```

### 3. Hedge Put Finder

Find 30 DTE, 5% OTM puts around $1.50:

```python
from market_data.marketdata_client import MarketDataClient

client = MarketDataClient()
iwm_price = 195.50

hedge_puts = client.get_hedge_puts(
    symbol='IWM',
    current_price=iwm_price,
    otm_pct=0.05,  # 5% OTM
    dte=30,
    max_price=1.50
)
```

### 4. Full Options Chain

Get complete options chain with filtering:

```python
from market_data import get_options_chain

# Get all 1 DTE puts
chain = get_options_chain(
    symbol='IWM',
    dte_min=1,
    dte_max=1,
    option_type='put'
)

# Columns: option_symbol, strike, bid, ask, mid, volume, 
#          open_interest, iv, delta, gamma, theta, vega, rho
```

## Automatic Fallback

The system automatically falls back to yfinance if:
- No Market Data API token is configured
- Market Data API is unavailable
- API request fails

You'll see log messages indicating which data source is being used.

## Verify It's Working

Check the app logs:

```bash
docker logs iwm-tracker-wheel-tracker-1 | grep "Market Data"
```

You should see:
```
Using Market Data App for IWM price (real-time)
```

If you see:
```
Using yfinance for IWM price (15-20 min delay)
```

Then it's using the free fallback.

## API Endpoints Used

The integration uses these Market Data App endpoints:

- `GET /v1/stocks/quotes/{symbol}/` - Real-time stock quotes
- `GET /v1/options/chain/{symbol}/` - Options chains with Greeks

## Rate Limits

**Trader Plan**: High rate limits suitable for active trading
- Sufficient for real-time monitoring
- Can fetch options chains multiple times per minute

## Cost Analysis

**Market Data App Trader Plan**: $75/month

**Benefits for Your Strategy**:
- Real-time data for better entry/exit timing
- Greeks for position analysis
- IV data for premium evaluation
- Options chain for finding optimal strikes

**Worth it if**:
- You're actively trading (daily)
- Timing matters for your entries
- You want to analyze Greeks before selling
- You're managing $500K+ account

**Stick with free yfinance if**:
- You're just tracking trades
- 15-20 min delay is acceptable
- You don't need options chain data

## Next Steps

Once configured, the enhanced app will show:
1. Real-time IWM price (no delay badge)
2. Options suggestions for 1 DTE puts
3. Hedge put recommendations
4. Greeks analysis for open positions

## Support

- Market Data App Docs: https://www.marketdata.app/docs/api/
- Market Data App Support: support@marketdata.app
- API Status: https://www.marketdata.app/status/

## Example: Finding Today's Best Put to Sell

```python
from market_data import get_iwm_price, get_1dte_puts_near_money
from strategy import get_position_sizing_recommendation

# Get current price
iwm_price = get_iwm_price()

# Get 1 DTE puts near the money
puts = get_1dte_puts_near_money(iwm_price)

# Find puts with target premium
for _, put in puts.iterrows():
    sizing = get_position_sizing_recommendation(
        option_price=put['mid'],
        account_value=1_000_000
    )
    
    if sizing['expected_premium'] >= 600:
        print(f"Strike: {put['strike']}")
        print(f"Mid: ${put['mid']:.2f}")
        print(f"Contracts: {sizing['contracts']}")
        print(f"Premium: ${sizing['expected_premium']:.0f}")
        print(f"Delta: {put['delta']:.3f}")
        print(f"IV: {put['iv']:.1%}")
        print("---")
```

This will help you find the optimal strike for your 0.08% daily premium target!
