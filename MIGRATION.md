# Migration from Streamlit to React + FastAPI

This document describes the migration from Streamlit to a React frontend with FastAPI backend.

## Architecture Changes

### Before (Streamlit)
- Single Python application using Streamlit
- All logic in Python
- Server-side rendering

### After (React + FastAPI)
- **Frontend**: React with Tailwind CSS (port 3000)
- **Backend**: FastAPI REST API (port 8000)
- Separation of concerns: UI and business logic

## Project Structure

```
iwm-tracker/
├── backend/              # FastAPI backend
│   ├── main.py          # FastAPI app entry point
│   ├── routers/         # API route handlers
│   │   ├── auth.py      # Authentication
│   │   ├── trades.py    # Trade management
│   │   ├── market_data.py
│   │   ├── analytics.py
│   │   └── recommendations.py
│   └── run.py           # Development server
├── frontend/            # React frontend
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── contexts/    # React contexts (Auth)
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
└── src/                 # Shared business logic (unchanged)
```

## Running the Application

### Development Mode

**Using Docker Compose**
```bash
docker-compose -f docker-compose.dev.yml up
```

### Access
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout

### Trades
- `GET /api/trades/` - List all trades
- `POST /api/trades/` - Create new trade
- `GET /api/trades/{id}` - Get specific trade

### Market Data
- `GET /api/market-data/iwm-price` - Get IWM price
- `GET /api/market-data/indicators/trend` - Get trend indicator
- `GET /api/market-data/indicators/cycle-swing` - Get cycle swing indicator

### Analytics
- `GET /api/analytics/performance` - Performance summary
- `GET /api/analytics/cost-basis` - Cost basis analysis
- `GET /api/analytics/capital-usage` - Capital usage stats
- `GET /api/analytics/monthly-premium` - Monthly premium data
- `GET /api/analytics/cumulative-premium` - Cumulative premium data
- `GET /api/analytics/open-positions` - Open option positions

### Recommendations
- `GET /api/recommendations/all` - Get all recommendations
- `GET /api/recommendations/position-sizing` - Position sizing recommendation
- `GET /api/recommendations/hedging` - Hedging recommendation

## Features Migrated

✅ Authentication (username/password)
✅ Trade management (add, list, view)
✅ Market data display (IWM price)
✅ Technical indicators (Ehler's Trend, Cycle Swing)
✅ Performance metrics
✅ Trade recommendations
✅ Analytics and charts
✅ Cost basis analysis
✅ Capital usage tracking
✅ Open positions management

## Authentication

The authentication system uses simple token-based auth. Tokens are stored in memory on the backend and in localStorage on the frontend.

**Note**: For production, consider implementing JWT tokens or OAuth2.

## Environment Variables

Create a `.env` file in the root directory:
```
ACCOUNT_SIZE=1000000
WHEEL_DB_PATH=data/wheel.db
MARKETDATA_API_TOKEN=your_token_here  # Optional
```

## Database

The database path can be configured via:
- Environment variable: `WHEEL_DB_PATH`
- API parameter: `db_path` (for testing with different databases)

## Next Steps

1. **Production Deployment**:
   - Build production React app: `cd frontend && npm run build`
   - Serve static files with FastAPI or nginx
   - Use proper JWT authentication
   - Set up HTTPS

2. **Testing**:
   - Add API tests for FastAPI endpoints
   - Add frontend component tests
   - Integration tests

3. **Improvements**:
   - Real-time updates with WebSockets
   - Better error handling
   - Loading states
   - Form validation
   - Responsive design improvements

