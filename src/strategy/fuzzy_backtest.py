"""
Fuzzy Logic Strategy Backtest Engine

Backtests the fuzzy logic trading strategy using historical SPX/SPY and VIX data.
Supports parameter optimization and performance analysis.
"""
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging

from src.market_data.historical_data import get_combined_market_data, get_vix_history
from src.strategy.fuzzy_strategy import FuzzyStrategy
from src.strategy.fuzzy_inputs import (
    normalize_vix,
    calculate_trend_normalized,
    calculate_cycle_normalized,
    get_fuzzy_inputs
)
from src.indicators.ehlers_trend import calculate_instantaneous_trend
from src.indicators.cycle_swing import calculate_cycle_swing

logger = logging.getLogger(__name__)


@dataclass
class FuzzyBacktestParams:
    """Tunable parameters for fuzzy logic strategy optimization"""
    
    # Membership function boundaries
    cycle_oversold_threshold: float = -0.4
    cycle_overbought_threshold: float = 0.4
    trend_down_threshold: float = -0.3
    trend_up_threshold: float = 0.3
    
    # Rule weights
    put_moneyness_weight: float = 1.0
    put_size_weight: float = 1.0
    call_sell_threshold: float = 0.6
    hedge_score_threshold: float = 0.4
    
    # Trading parameters
    target_dte: int = 1  # Target days to expiration for puts (1 DTE, or 3 DTE for Friday)
    hedge_dte: int = 30  # Days to expiration for hedge puts
    max_hedge_notional_pct: float = 0.5  # Max hedge as % of stock exposure
    
    # Position sizing
    target_daily_premium_pct: float = 0.0008  # 0.08% daily target
    min_contract_premium: float = 50.0  # Minimum premium per contract to trade
    
    # Hedge parameters
    hedge_otm_pct_low_vix: float = 12.0  # OTM % when VIX is low
    hedge_otm_pct_high_vix: float = 6.0  # OTM % when VIX is high
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for optimization"""
        return {
            'cycle_oversold_threshold': self.cycle_oversold_threshold,
            'cycle_overbought_threshold': self.cycle_overbought_threshold,
            'trend_down_threshold': self.trend_down_threshold,
            'trend_up_threshold': self.trend_up_threshold,
            'put_moneyness_weight': self.put_moneyness_weight,
            'put_size_weight': self.put_size_weight,
            'call_sell_threshold': self.call_sell_threshold,
            'hedge_score_threshold': self.hedge_score_threshold,
            'target_dte': self.target_dte,
            'hedge_dte': self.hedge_dte,
            'max_hedge_notional_pct': self.max_hedge_notional_pct,
            'target_daily_premium_pct': self.target_daily_premium_pct,
            'min_contract_premium': self.min_contract_premium,
            'hedge_otm_pct_low_vix': self.hedge_otm_pct_low_vix,
            'hedge_otm_pct_high_vix': self.hedge_otm_pct_high_vix,
        }
    
    @classmethod
    def from_dict(cls, params: Dict) -> 'FuzzyBacktestParams':
        """Create from dictionary"""
        return cls(**params)


@dataclass
class OptionPosition:
    """Represents an option position"""
    symbol: str
    strike: float
    expiration: date
    option_type: str  # 'put' or 'call'
    quantity: int  # Positive = long, negative = short
    entry_price: float
    entry_date: date
    current_price: float = 0.0
    delta: float = 0.0
    iv: float = 0.0
    
    @property
    def dte(self) -> int:
        """Days to expiration"""
        return (self.expiration - date.today()).days
    
    @property
    def is_expired(self) -> bool:
        """Check if option is expired"""
        return self.expiration <= date.today()
    
    @property
    def unrealized_pnl(self) -> float:
        """Unrealized PnL for this position"""
        if self.quantity > 0:  # Long position
            return (self.current_price - self.entry_price) * abs(self.quantity) * 100
        else:  # Short position
            return (self.entry_price - self.current_price) * abs(self.quantity) * 100


@dataclass
class PortfolioState:
    """Current portfolio state"""
    cash: float
    stock_shares: int = 0
    stock_cost_basis: float = 0.0
    options: List[OptionPosition] = field(default_factory=list)
    hedge_options: List[OptionPosition] = field(default_factory=list)
    
    # Track daily metrics
    daily_premium_collected: float = 0.0
    daily_premium_target: float = 0.0
    
    def total_value(self, current_price: float) -> float:
        """Calculate total portfolio value"""
        stock_value = self.stock_shares * current_price
        options_value = sum(opt.unrealized_pnl for opt in self.options + self.hedge_options)
        return self.cash + stock_value + options_value
    
    def buying_power_used(self, current_price: float) -> float:
        """Calculate buying power used (simplified)"""
        # Stock capital
        stock_capital = self.stock_shares * current_price
        
        # Cash-secured puts (short puts require cash = strike * 100 * contracts)
        csp_capital = 0.0
        for opt in self.options:
            if opt.option_type == 'put' and opt.quantity < 0:  # Short puts
                csp_capital += opt.strike * 100 * abs(opt.quantity)
        
        return stock_capital + csp_capital
    
    def buying_power_available(self, total_value: float, current_price: float) -> float:
        """Calculate available buying power"""
        used = self.buying_power_used(current_price)
        return total_value - used


@dataclass
class BacktestMetrics:
    """Performance metrics from backtest"""
    total_return: float
    cagr: float
    max_drawdown: float
    sharpe_ratio: float
    mar_ratio: float  # CAGR / Max Drawdown
    days_target_met: int
    days_target_met_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_trade_return: float
    
    # Hedged vs unhedged comparison
    hedged_drawdown: float = 0.0
    unhedged_drawdown: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'total_return': self.total_return,
            'cagr': self.cagr,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'mar_ratio': self.mar_ratio,
            'days_target_met': self.days_target_met,
            'days_target_met_pct': self.days_target_met_pct,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'avg_trade_return': self.avg_trade_return,
            'hedged_drawdown': self.hedged_drawdown,
            'unhedged_drawdown': self.unhedged_drawdown,
        }


class FuzzyBacktestEngine:
    """
    Backtest engine for fuzzy logic trading strategy
    """
    
    def __init__(
        self,
        initial_capital: float = 1_000_000.0,
        params: Optional[FuzzyBacktestParams] = None,
        use_spy: bool = True
    ):
        """
        Initialize backtest engine
        
        Args:
            initial_capital: Starting capital
            params: Fuzzy logic parameters (uses defaults if None)
            use_spy: If True, use SPY; if False, use SPX
        """
        self.initial_capital = initial_capital
        self.params = params or FuzzyBacktestParams()
        self.use_spy = use_spy
        self.symbol = "SPY" if use_spy else "SPX"
        
        self.fuzzy_strategy = FuzzyStrategy()
        self.portfolio = PortfolioState(cash=initial_capital)
        
        # Track daily values for metrics
        self.daily_values: List[float] = []
        self.daily_dates: List[date] = []
        self.daily_premiums: List[float] = []
        self.daily_targets: List[float] = []
        
        # Track trades
        self.trades: List[Dict] = []
    
    def _estimate_option_price(
        self,
        current_price: float,
        strike: float,
        option_type: str,
        dte: int,
        vix: float,
        moneyness: float = 0.0
    ) -> float:
        """
        Estimate option price using Black-Scholes approximation
        
        This is a simplified model for backtesting. In production, use real option prices.
        
        Args:
            current_price: Current underlying price
            strike: Strike price
            option_type: 'put' or 'call'
            dte: Days to expiration
            vix: Current VIX level
            moneyness: Moneyness offset (for puts: negative = ITM)
        
        Returns:
            Estimated option price
        """
        # Simplified Black-Scholes approximation
        # For puts: intrinsic + time value
        # For calls: intrinsic + time value
        
        if option_type == 'put':
            intrinsic = max(0, strike - current_price)
            # Time value based on VIX and DTE
            # Use strike price (not current_price) for time value calculation
            # Scale factor of 0.1 gives more realistic option prices
            # For ATM: ~1-3% of strike for 7-14 DTE options
            time_value = (vix / 100) * strike * np.sqrt(dte / 365) * 0.1
            # Adjust for moneyness - OTM options have less time value
            if moneyness < 0:  # ITM
                time_value *= (1 + abs(moneyness) * 0.15)
            else:  # OTM
                time_value *= max(0.1, 1 - moneyness * 0.15)  # Cap at 10% of base
            return intrinsic + time_value
        else:  # call
            intrinsic = max(0, current_price - strike)
            time_value = (vix / 100) * strike * np.sqrt(dte / 365) * 0.1
            if moneyness > 0:  # OTM
                time_value *= max(0.1, 1 - moneyness * 0.15)
            return intrinsic + time_value
    
    def _calculate_portfolio_metrics_for_fuzzy(
        self,
        current_price: float,
        vix: float
    ) -> Dict[str, float]:
        """
        Calculate portfolio metrics needed for fuzzy logic inputs
        
        Returns:
            Dictionary with bp_frac, stock_weight, delta_port, premium_gap
        """
        total_value = self.portfolio.total_value(current_price)
        
        if total_value <= 0:
            return {
                'bp_frac': 1.0,
                'stock_weight': 0.0,
                'delta_port': 0.0,
                'premium_gap': 1.0
            }
        
        # Buying power fraction
        bp_used = self.portfolio.buying_power_used(current_price)
        bp_frac = 1.0 - (bp_used / total_value) if total_value > 0 else 1.0
        bp_frac = max(0.0, min(1.0, bp_frac))
        
        # Stock weight
        stock_value = self.portfolio.stock_shares * current_price
        stock_weight = stock_value / total_value if total_value > 0 else 0.0
        
        # Portfolio delta (simplified)
        # Long stock = +1 delta per share
        # Short puts = positive delta (approx 0.3-0.5 per contract)
        # Long hedge puts = negative delta
        delta_port = stock_weight  # Simplified
        for opt in self.portfolio.options:
            if opt.option_type == 'put' and opt.quantity < 0:  # Short puts
                delta_port += 0.4 * (abs(opt.quantity) * 100 * opt.strike) / total_value
        for opt in self.portfolio.hedge_options:
            if opt.option_type == 'put' and opt.quantity > 0:  # Long hedge puts
                delta_port -= 0.3 * (abs(opt.quantity) * 100 * opt.strike) / total_value
        
        # Premium gap
        target_premium = total_value * self.params.target_daily_premium_pct
        realized_premium = self.portfolio.daily_premium_collected
        if target_premium > 0:
            premium_gap = max(0.0, 1.0 - (realized_premium / target_premium))
        else:
            premium_gap = 1.0
        
        return {
            'bp_frac': bp_frac,
            'stock_weight': stock_weight,
            'delta_port': delta_port,
            'premium_gap': premium_gap
        }
    
    def _execute_put_sale(
        self,
        current_price: float,
        vix: float,
        put_moneyness: float,
        put_size_frac: float,
        trade_date: date
    ) -> Optional[OptionPosition]:
        """
        Execute put sale based on fuzzy logic outputs
        
        Args:
            current_price: Current underlying price
            vix: Current VIX
            put_moneyness: Fuzzy output for put moneyness
            put_size_frac: Fuzzy output for position size fraction
            trade_date: Trade date
        
        Returns:
            OptionPosition if trade executed, None otherwise
        """
        # Calculate target strike
        # put_moneyness: negative = ITM, 0 = ATM, positive = OTM
        strike_offset = put_moneyness * current_price * 0.02  # 2% per unit
        target_strike = current_price - strike_offset
        target_strike = round(target_strike / 0.5) * 0.5  # Round to nearest $0.50
        
        # Calculate expiration - 1 DTE (or 3 DTE for Friday trades)
        # If today is Friday, use 3 DTE (expires Monday), otherwise 1 DTE
        if trade_date.weekday() == 4:  # Friday (0=Monday, 4=Friday)
            dte = 3  # Expires Monday (3 days)
        else:
            dte = 1  # Expires next day
        expiration = trade_date + timedelta(days=dte)
        
        # Estimate option price using calculated DTE (1 or 3 for Friday)
        option_price = self._estimate_option_price(
            current_price, target_strike, 'put', dte, vix, put_moneyness
        )
        
        if option_price < self.params.min_contract_premium / 100:
            return None  # Premium too low
        
        # Calculate position size
        total_value = self.portfolio.total_value(current_price)
        target_premium = total_value * self.params.target_daily_premium_pct
        remaining_target = target_premium - self.portfolio.daily_premium_collected
        
        if remaining_target <= 0:
            return None  # Already met target
        
        # Size based on fuzzy output
        target_notional = remaining_target * put_size_frac
        contracts = int(target_notional / (option_price * 100))
        
        if contracts <= 0:
            return None
        
        # Check buying power
        required_bp = target_strike * 100 * contracts
        available_bp = self.portfolio.buying_power_available(total_value, current_price)
        
        if required_bp > available_bp:
            contracts = int(available_bp / (target_strike * 100))
            if contracts <= 0:
                return None
        
        # Execute trade
        premium_collected = option_price * 100 * contracts
        self.portfolio.cash += premium_collected
        self.portfolio.daily_premium_collected += premium_collected
        
        position = OptionPosition(
            symbol=self.symbol,
            strike=target_strike,
            expiration=expiration,
            option_type='put',
            quantity=-contracts,  # Negative = short
            entry_price=option_price,
            entry_date=trade_date,
            current_price=option_price,
            iv=vix / 100
        )
        
        self.portfolio.options.append(position)
        
        self.trades.append({
            'date': trade_date,
            'type': 'sell_put',
            'strike': target_strike,
            'contracts': contracts,
            'premium': premium_collected,
            'moneyness': put_moneyness,
            'size_frac': put_size_frac
        })
        
        return position
    
    def _execute_hedge(
        self,
        current_price: float,
        vix: float,
        hedge_score: float,
        hedge_otm_pct: float,
        trade_date: date
    ) -> Optional[OptionPosition]:
        """
        Execute hedge put purchase
        
        Args:
            current_price: Current underlying price
            vix: Current VIX
            hedge_score: Fuzzy output for hedge score
            hedge_otm_pct: Fuzzy output for hedge OTM %
            trade_date: Trade date
        
        Returns:
            OptionPosition if trade executed, None otherwise
        """
        if hedge_score < self.params.hedge_score_threshold:
            return None
        
        # Calculate hedge notional
        total_value = self.portfolio.total_value(current_price)
        stock_exposure = self.portfolio.stock_shares * current_price
        max_hedge_notional = stock_exposure * self.params.max_hedge_notional_pct
        target_hedge_notional = hedge_score * max_hedge_notional
        
        # Calculate current hedge
        current_hedge_notional = sum(
            opt.strike * 100 * abs(opt.quantity)
            for opt in self.portfolio.hedge_options
            if opt.option_type == 'put' and opt.quantity > 0
        )
        
        delta_notional = target_hedge_notional - current_hedge_notional
        
        if delta_notional <= 0:
            return None  # Already hedged enough
        
        # Calculate strike
        target_strike = current_price * (1 - hedge_otm_pct / 100)
        target_strike = round(target_strike / 0.5) * 0.5
        
        # Calculate expiration
        expiration = trade_date + timedelta(days=self.params.hedge_dte)
        
        # Estimate option price
        option_price = self._estimate_option_price(
            current_price, target_strike, 'put', self.params.hedge_dte, vix, 0.0
        )
        
        # Calculate contracts needed
        contracts = int(delta_notional / (target_strike * 100))
        if contracts <= 0:
            return None
        
        # Check if we have enough cash
        cost = option_price * 100 * contracts
        if cost > self.portfolio.cash:
            contracts = int(self.portfolio.cash / (option_price * 100))
            if contracts <= 0:
                return None
            cost = option_price * 100 * contracts
        
        # Execute trade
        self.portfolio.cash -= cost
        
        position = OptionPosition(
            symbol=self.symbol,
            strike=target_strike,
            expiration=expiration,
            option_type='put',
            quantity=contracts,  # Positive = long
            entry_price=option_price,
            entry_date=trade_date,
            current_price=option_price,
            iv=vix / 100
        )
        
        self.portfolio.hedge_options.append(position)
        
        self.trades.append({
            'date': trade_date,
            'type': 'buy_hedge_put',
            'strike': target_strike,
            'contracts': contracts,
            'cost': cost,
            'hedge_score': hedge_score
        })
        
        return position
    
    def _update_option_prices(
        self,
        current_price: float,
        vix: float,
        current_date: date
    ):
        """Update option prices based on current market conditions"""
        for opt in self.portfolio.options + self.portfolio.hedge_options:
            if opt.is_expired:
                continue
            
            dte = (opt.expiration - current_date).days
            if dte <= 0:
                continue
            
            # Calculate moneyness
            if opt.option_type == 'put':
                moneyness = (current_price - opt.strike) / opt.strike
            else:
                moneyness = (opt.strike - current_price) / opt.strike
            
            opt.current_price = self._estimate_option_price(
                current_price, opt.strike, opt.option_type, dte, vix, moneyness
            )
    
    def _handle_expirations(self, current_date: date, current_price: float):
        """Handle option expirations and assignments"""
        # Handle regular options
        expired_options = [opt for opt in self.portfolio.options if opt.is_expired]
        
        for opt in expired_options:
            if opt.option_type == 'put' and opt.quantity < 0:  # Short put expired
                if current_price < opt.strike:  # ITM - assigned
                    # Buy stock at strike price
                    shares_to_buy = abs(opt.quantity) * 100
                    cost = opt.strike * shares_to_buy
                    
                    if self.portfolio.cash >= cost:
                        self.portfolio.cash -= cost
                        # Update cost basis
                        old_shares = self.portfolio.stock_shares
                        total_cost = self.portfolio.stock_cost_basis * old_shares + cost
                        self.portfolio.stock_shares += shares_to_buy
                        if self.portfolio.stock_shares > 0:
                            self.portfolio.stock_cost_basis = total_cost / self.portfolio.stock_shares
                # Option expired, remove from portfolio
                self.portfolio.options.remove(opt)
        
        # Handle hedge options
        expired_hedges = [opt for opt in self.portfolio.hedge_options if opt.is_expired]
        for opt in expired_hedges:
            # Hedge puts expire worthless or are exercised
            # For simplicity, assume they expire worthless if OTM
            if opt.option_type == 'put' and opt.quantity > 0:  # Long hedge put
                if current_price < opt.strike:  # ITM - exercise
                    # Sell stock at strike (protective put)
                    shares_to_sell = min(opt.quantity * 100, self.portfolio.stock_shares)
                    proceeds = opt.strike * shares_to_sell
                    self.portfolio.cash += proceeds
                    self.portfolio.stock_shares -= shares_to_sell
            self.portfolio.hedge_options.remove(opt)
    
    def run(
        self,
        start_date: date,
        end_date: date
    ) -> BacktestMetrics:
        """
        Run backtest
        
        Args:
            start_date: Start date for backtest
            end_date: End date for backtest
        
        Returns:
            BacktestMetrics with performance results
        """
        logger.info(f"Starting backtest from {start_date} to {end_date}")
        
        # Get market data
        market_data = get_combined_market_data(start_date, end_date, self.use_spy)
        if market_data.empty:
            raise ValueError("No market data available for backtest period")
        
        # Get VIX history for normalization
        vix_history = get_vix_history(start_date, end_date)
        
        # Reset portfolio
        self.portfolio = PortfolioState(cash=self.initial_capital)
        self.daily_values = []
        self.daily_dates = []
        self.daily_premiums = []
        self.daily_targets = []
        self.trades = []
        
        # Prepare price series for indicators (need enough history)
        # Get extra history for indicator calculation
        indicator_start = start_date - timedelta(days=100)
        indicator_data = get_combined_market_data(indicator_start, end_date, self.use_spy)
        
        if indicator_data.empty:
            raise ValueError("No indicator data available")
        
        # Calculate indicators for all dates
        close_prices = indicator_data['Close']
        hl2_prices = (indicator_data['High'] + indicator_data['Low']) / 2
        
        # Calculate indicators
        trend_result = calculate_instantaneous_trend(hl2_prices)
        cycle_result = calculate_cycle_swing(close_prices)
        
        # Main simulation loop
        for current_date in pd.date_range(start=start_date, end=end_date, freq='D'):
            current_date = current_date.date()
            
            # Skip weekends (no market data)
            if current_date not in market_data.index.date:
                continue
            
            # Get current market data
            day_data = market_data.loc[market_data.index.date == current_date]
            if day_data.empty:
                continue
            
            current_price = float(day_data['Close'].iloc[0])
            current_vix = float(day_data['VIX'].iloc[0]) if 'VIX' in day_data.columns and pd.notna(day_data['VIX'].iloc[0]) else 20.0
            
            # Reset daily premium tracking
            self.portfolio.daily_premium_collected = 0.0
            total_value = self.portfolio.total_value(current_price)
            self.portfolio.daily_premium_target = total_value * self.params.target_daily_premium_pct
            
            # Update option prices
            self._update_option_prices(current_price, current_vix, current_date)
            
            # Handle expirations
            self._handle_expirations(current_date, current_price)
            
            # Get indicators for current date
            if current_date in close_prices.index.date:
                date_idx = list(close_prices.index.date).index(current_date)
                if date_idx >= 50:  # Need enough history for indicators
                    # Get recent series for normalization
                    recent_hl2 = hl2_prices.iloc[max(0, date_idx-100):date_idx+1]
                    recent_close = close_prices.iloc[max(0, date_idx-100):date_idx+1]
                    
                    trend = calculate_trend_normalized(recent_hl2)
                    cycle = calculate_cycle_normalized(recent_close)
                else:
                    trend = 0.0
                    cycle = 0.0
            else:
                trend = 0.0
                cycle = 0.0
            
            # Normalize VIX
            vix_norm = normalize_vix(current_vix, vix_history)
            
            # Calculate portfolio metrics
            portfolio_metrics = self._calculate_portfolio_metrics_for_fuzzy(current_price, current_vix)
            
            # Get fuzzy inputs
            fuzzy_inputs = {
                'trend': trend,
                'cycle': cycle,
                'vix_norm': vix_norm,
                **portfolio_metrics
            }
            
            # Calculate fuzzy outputs
            put_moneyness = self.fuzzy_strategy.calculate_put_moneyness(
                fuzzy_inputs['cycle'],
                fuzzy_inputs['trend']
            ) * self.params.put_moneyness_weight
            
            put_size_frac = self.fuzzy_strategy.calculate_put_size_frac(
                fuzzy_inputs['premium_gap'],
                fuzzy_inputs['vix_norm'],
                fuzzy_inputs['bp_frac']
            ) * self.params.put_size_weight
            put_size_frac = min(1.0, put_size_frac)
            
            # Execute put sale if conditions are met
            if put_size_frac > 0.1:  # Only trade if size fraction is meaningful
                self._execute_put_sale(
                    current_price, current_vix, put_moneyness, put_size_frac, current_date
                )
            
            # Calculate hedge score
            hedge_score, hedge_otm_pct = self.fuzzy_strategy.calculate_hedge_score(
                fuzzy_inputs['vix_norm'],
                fuzzy_inputs['cycle'],
                fuzzy_inputs['trend'],
                fuzzy_inputs['stock_weight'],
                fuzzy_inputs['delta_port']
            )
            
            # Adjust hedge OTM based on VIX
            if vix_norm < 0.3:
                hedge_otm_pct = self.params.hedge_otm_pct_low_vix
            elif vix_norm > 0.7:
                hedge_otm_pct = self.params.hedge_otm_pct_high_vix
            
            # Execute hedge if needed
            if hedge_score >= self.params.hedge_score_threshold:
                self._execute_hedge(
                    current_price, current_vix, hedge_score, hedge_otm_pct, current_date
                )
            
            # Record daily metrics
            total_value = self.portfolio.total_value(current_price)
            self.daily_values.append(total_value)
            self.daily_dates.append(current_date)
            self.daily_premiums.append(self.portfolio.daily_premium_collected)
            self.daily_targets.append(self.portfolio.daily_premium_target)
        
        # Calculate final metrics
        return self._calculate_metrics()
    
    def _calculate_metrics(self) -> BacktestMetrics:
        """Calculate performance metrics from backtest results"""
        if not self.daily_values:
            return BacktestMetrics(
                total_return=0.0, cagr=0.0, max_drawdown=0.0,
                sharpe_ratio=0.0, mar_ratio=0.0,
                days_target_met=0, days_target_met_pct=0.0,
                total_trades=0, winning_trades=0, losing_trades=0,
                avg_trade_return=0.0
            )
        
        values = np.array(self.daily_values)
        dates = np.array(self.daily_dates)
        
        # Total return
        total_return = (values[-1] - values[0]) / values[0]
        
        # CAGR
        days = (dates[-1] - dates[0]).days
        years = days / 365.25
        if years > 0:
            cagr = (values[-1] / values[0]) ** (1 / years) - 1
        else:
            cagr = 0.0
        
        # Max drawdown
        peak = np.maximum.accumulate(values)
        drawdown = (values - peak) / peak
        max_drawdown = abs(np.min(drawdown))
        
        # Sharpe ratio (annualized)
        returns = np.diff(values) / values[:-1]
        if len(returns) > 0 and np.std(returns) > 0:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)  # Annualized
        else:
            sharpe_ratio = 0.0
        
        # MAR ratio
        mar_ratio = cagr / max_drawdown if max_drawdown > 0 else 0.0
        
        # Days target met
        premiums = np.array(self.daily_premiums)
        targets = np.array(self.daily_targets)
        days_target_met = np.sum(premiums >= targets * 0.8)  # 80% of target counts as met
        days_target_met_pct = (days_target_met / len(premiums) * 100) if len(premiums) > 0 else 0.0
        
        # Trade statistics
        total_trades = len(self.trades)
        # Simplified: count winning vs losing (would need to track closes)
        winning_trades = 0
        losing_trades = 0
        
        # Calculate average trade return (simplified)
        avg_trade_return = 0.0
        
        return BacktestMetrics(
            total_return=total_return,
            cagr=cagr,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            mar_ratio=mar_ratio,
            days_target_met=days_target_met,
            days_target_met_pct=days_target_met_pct,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_trade_return=avg_trade_return
        )

