# IWM Put Selling Strategy Tracker - Docker Quick Start

## 🚀 Quick Start with Docker

The easiest way to run the IWM Tracker is using Docker Compose:

### Prerequisites
- Docker Desktop installed and running
- No Python installation needed!

### Start the App

```bash
docker-compose up -d
```

That's it! The app will be available at **http://localhost:8501**

### Docker Commands

```bash
# Start the app
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the app
docker-compose down

# Restart the app
docker-compose restart

# Rebuild after code changes
docker-compose up --build -d
```

## 📊 Features

- **Real-time Market Data**: IWM price (15-20 min delay via yfinance)
- **Technical Indicators**: 
  - Ehler's Instantaneous Trendline
  - Cycle Swing Momentum
- **Performance Tracking**: Annualized returns, win rate, Sharpe ratio
- **Position Sizing**: Automatic recommendations for 0.08% daily target
- **Trade Management**: Full trade history and cost basis analysis

## 🎯 Your Strategy

- **Target**: 18-20% annual return
- **Daily Premium**: $600-800 (0.08% of account)
- **Position Size**: 5-10 contracts
- **Exit**: Close at $0.05 per contract
- **Rolling**: ITM puts for 0.05-0.08% additional premium

## 📁 Data Persistence

Your trade data is stored in `wheel.db` which is automatically mounted to the Docker container. Your data persists even when you stop/restart the container.

## 🔧 Configuration

Edit `src/strategy/rules.py` to customize:
- Account size (default: $1M)
- Daily premium target (default: 0.08%)
- Position size limits (default: 5-10 contracts)
- Close threshold (default: $0.05)

After changes, rebuild:
```bash
docker-compose up --build -d
```

## 🆘 Troubleshooting

**App won't start?**
```bash
# Check if Docker is running
docker info

# Check logs
docker-compose logs

# Force rebuild
docker-compose down
docker-compose up --build -d
```

**Port 8501 already in use?**
Edit `docker-compose.yml` and change the port mapping:
```yaml
ports:
  - "8502:8501"  # Use port 8502 instead
```

## 📈 Next Steps

When ready for real-time data:
1. Sign up for Tradier Brokerage ($10/month)
2. Get API credentials
3. Update `src/market_data/price_fetcher.py`
4. Rebuild the container

## 🎉 Enjoy!

Your IWM put selling strategy tracker is now running in Docker with zero Python environment hassles!
