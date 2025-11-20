"""
Strategy Rules and Constants

Based on user's IWM put selling strategy:
- Target 0.08% daily premium on $1M account = $800/day
- Close positions at $0.05 per contract
- Roll ITM puts if can collect 0.05-0.08% additional premium
- Prefer 1 DTE options
- Sell 5-10 contracts to target $600-800/day
"""

# Premium targets
TARGET_DAILY_PREMIUM_PCT = 0.0008  # 0.08% per day
TARGET_DAILY_PREMIUM_MIN = 600  # Minimum $600/day
TARGET_DAILY_PREMIUM_MAX = 800  # Maximum $800/day

# Position closing
CLOSE_THRESHOLD = 0.05  # Close when option reaches $0.05

# Rolling strategy
ROLL_PREMIUM_MIN = 0.0005  # 0.05% minimum additional premium for rolls
ROLL_PREMIUM_MAX = 0.0008  # 0.08% maximum additional premium for rolls

# Option preferences
PREFERRED_DTE = 1  # 1 day to expiration
MAX_DTE = 3  # Maximum days to expiration to consider

# Position sizing
MIN_CONTRACTS = 5  # Minimum contracts to sell
MAX_CONTRACTS = 10  # Maximum contracts to sell
CONTRACTS_PER_100_SHARES = 1  # 1 contract = 100 shares

# Hedge strategy
HEDGE_PUT_OTM_PCT = 0.05  # 5% out of the money
HEDGE_PUT_TARGET_PRICE = 1.50  # Target $1.50 per contract ($150 per contract)
HEDGE_PUT_DTE = 30  # 30 days to expiration

# DITM call conversion (when assigned on too many puts)
DITM_CALL_DTE = 90  # 90 days out
DITM_CALL_MIN_DELTA = 0.80  # Minimum 0.80 delta

# Account constraints
DEFAULT_ACCOUNT_SIZE = 1_000_000  # $1M default account size
CASH_RESERVE_PCT = 0.05  # Keep 5% cash reserve
MAX_BUYING_POWER_USAGE = 0.95  # Use max 95% of buying power
