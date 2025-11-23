"""
Fuzzy Logic Enhanced Recommendations

Integrates fuzzy logic strategy with the recommendation engine
"""
from typing import List, Dict, Optional, Tuple
from datetime import date, timedelta
import logging
import pandas as pd

from src.wheeltracker.models import Trade
from src.wheeltracker.analytics import trades_to_dataframe
from src.market_data import get_iwm_price
from src.strategy.fuzzy_strategy import FuzzyStrategy
from src.strategy.fuzzy_inputs import (
    get_fuzzy_inputs,
    calculate_assigned_share_metrics
)
from src.strategy.trade_recommendations import TradeRecommendation
from src.strategy.position_manager import calculate_capital_usage, get_current_positions
from src.strategy.premium_calculator import (
    calculate_daily_target,
    calculate_contracts_needed,
    calculate_expected_premium
)
from src.strategy.rules import TARGET_DAILY_PREMIUM_PCT
from src.market_data.marketdata_client import MarketDataClient

logger = logging.getLogger(__name__)


class FuzzyRecommendationEngine:
    """
    Fuzzy logic enhanced recommendation engine
    """
    
    def __init__(self):
        self.fuzzy_strategy = FuzzyStrategy()
    
    def get_fuzzy_put_recommendations(
        self,
        trades: List[Trade],
        account_value: float,
        iwm_price: float,
        vix_value: Optional[float] = None,
        vix_history: Optional[pd.Series] = None
    ) -> List[TradeRecommendation]:
        """
        Get put selling recommendations using fuzzy logic
        
        Args:
            trades: List of all trades
            account_value: Total account value
            iwm_price: Current IWM price
            vix_value: Current VIX value (optional)
            vix_history: Historical VIX series (optional)
            
        Returns:
            List of put selling recommendations
        """
        recommendations = []
        
        # Get fuzzy inputs
        fuzzy_inputs = get_fuzzy_inputs(
            trades, account_value, vix_value, vix_history, {'IWM': iwm_price}
        )
        
        # Calculate put moneyness using fuzzy logic
        put_moneyness = self.fuzzy_strategy.calculate_put_moneyness(
            fuzzy_inputs['cycle'],
            fuzzy_inputs['trend']
        )
        
        # Calculate put size fraction
        put_size_frac = self.fuzzy_strategy.calculate_put_size_frac(
            fuzzy_inputs['premium_gap'],
            fuzzy_inputs['vix_norm'],
            fuzzy_inputs['bp_frac']
        )
        
        # Convert moneyness to strike price
        # put_moneyness: -3 (ITM) to +3 (OTM)
        # For IWM, 1% ≈ $2-3, so we'll use ~$1 per unit
        strike_offset = put_moneyness * 2.0  # $2 per unit
        target_strike = iwm_price - strike_offset  # Negative moneyness = ITM (lower strike)
        
        # Round to nearest $0.50
        target_strike = round(target_strike * 2) / 2
        
        # Get available puts
        try:
            md_client = MarketDataClient()
            puts = md_client.get_options_chain(
                symbol='IWM',
                dte_min=1,
                dte_max=3,
                option_type='put',
                strike_min=target_strike - 2.0,
                strike_max=target_strike + 2.0
            )
            
            if puts.empty:
                logger.warning("No puts available for fuzzy recommendations")
                return []
            
            # Find put closest to target strike
            puts['strike_diff'] = abs(puts['strike'] - target_strike)
            puts = puts.sort_values('strike_diff')
            
            if puts.empty:
                return []
            
            best_put = puts.iloc[0]
            put_price = best_put['mid']
            
            # Calculate position sizing with fuzzy size fraction
            target_premium = calculate_daily_target(account_value)
            adjusted_target = target_premium * put_size_frac
            
            premium_per_contract = put_price * 100
            contracts = calculate_contracts_needed(premium_per_contract, adjusted_target)
            
            expected_premium = calculate_expected_premium(put_price, contracts)
            
            # Generate reason
            moneyness_desc = "ITM" if put_moneyness < 0 else ("ATM" if abs(put_moneyness) < 0.5 else "OTM")
            reason = (
                f"🎯 FUZZY PUT: {moneyness_desc} (moneyness={put_moneyness:.1f}), "
                f"size_frac={put_size_frac:.2f}, cycle={fuzzy_inputs['cycle']:.2f}, "
                f"trend={fuzzy_inputs['trend']:.2f}"
            )
            
            expiration_date = date.today() + timedelta(days=1)
            
            rec = TradeRecommendation(
                symbol='IWM',
                option_symbol=best_put['option_symbol'],
                strike=best_put['strike'],
                expiration=expiration_date,
                option_type='put',
                bid=best_put['bid'],
                ask=best_put['ask'],
                mid=put_price,
                recommended_price=put_price,
                recommended_contracts=contracts,
                expected_premium=expected_premium,
                premium_pct=(expected_premium / account_value) * 100,
                delta=best_put.get('delta'),
                iv=best_put.get('iv'),
                volume=best_put.get('volume'),
                open_interest=best_put.get('open_interest'),
                reason=reason,
                confidence="high" if put_size_frac > 0.7 else "medium",
                action_type="open_put"
            )
            
            recommendations.append(rec)
            
        except Exception as e:
            logger.error(f"Error generating fuzzy put recommendations: {e}")
        
        return recommendations
    
    def get_fuzzy_call_recommendations(
        self,
        trades: List[Trade],
        account_value: float,
        iwm_price: float,
        vix_value: Optional[float] = None
    ) -> List[TradeRecommendation]:
        """
        Get covered call recommendations using fuzzy logic
        
        Args:
            trades: List of all trades
            account_value: Total account value
            iwm_price: Current IWM price
            vix_value: Current VIX value (optional)
            
        Returns:
            List of covered call recommendations
        """
        recommendations = []
        
        # Get current positions
        current_positions = get_current_positions(trades)
        stock_positions = current_positions.get('stock', {})
        iwm_shares = stock_positions.get('IWM', 0)
        
        if iwm_shares < 100:
            return []
        
        # Get fuzzy inputs
        fuzzy_inputs = get_fuzzy_inputs(
            trades, account_value, vix_value, None, {'IWM': iwm_price}
        )
        
        # Calculate metrics for assigned shares
        share_metrics = calculate_assigned_share_metrics(trades, 'IWM', iwm_price)
        
        # Calculate call sell score
        # For distance from BE, we'll use a candidate strike
        # We'll iterate through potential strikes
        try:
            md_client = MarketDataClient()
            
            # Get available calls
            calls = md_client.get_options_chain(
                symbol='IWM',
                dte_min=1,
                dte_max=7,
                option_type='call',
                strike_min=iwm_price * 0.95,
                strike_max=iwm_price * 1.10
            )
            
            if calls.empty:
                return []
            
            # Calculate call sell score for each potential strike
            best_call = None
            best_score = 0.0
            
            for _, call in calls.iterrows():
                strike = call['strike']
                cost_basis_per_share = share_metrics.get('cost_basis', iwm_price * 0.95)
                
                # Distance from breakeven
                dist_from_be = (strike - cost_basis_per_share) / cost_basis_per_share if cost_basis_per_share > 0 else 0.0
                
                # Premium yield (annualized approximation)
                premium = call['mid']
                premium_yield = (premium / iwm_price) * (365 / 7)  # Rough annualized for 7 DTE
                
                # Calculate call sell score
                call_sell_score = self.fuzzy_strategy.calculate_call_sell_score(
                    share_metrics['unreal_pnl_pct'],
                    dist_from_be,
                    share_metrics['iv_rank'],
                    premium_yield
                )
                
                if call_sell_score > best_score:
                    best_score = call_sell_score
                    best_call = call
            
            # Only recommend if score is above threshold
            if best_score < 0.6 or best_call is None:
                return []
            
            # Calculate call moneyness
            call_moneyness = self.fuzzy_strategy.calculate_call_moneyness(
                fuzzy_inputs['cycle'],
                fuzzy_inputs['trend']
            )
            
            # Determine contracts to sell
            contracts_available = iwm_shares // 100
            contracts_to_sell = min(contracts_available, int(contracts_available * best_score))
            
            expected_premium = calculate_expected_premium(best_call['mid'], contracts_to_sell)
            
            expiration_date = date.today() + timedelta(days=7)
            
            reason = (
                f"📞 FUZZY CALL: sell_score={best_score:.2f}, "
                f"moneyness={call_moneyness:.1f}, unreal_pnl={share_metrics['unreal_pnl_pct']*100:.1f}%"
            )
            
            rec = TradeRecommendation(
                symbol='IWM',
                option_symbol=best_call['option_symbol'],
                strike=best_call['strike'],
                expiration=expiration_date,
                option_type='call',
                bid=best_call['bid'],
                ask=best_call['ask'],
                mid=best_call['mid'],
                recommended_price=best_call['mid'],
                recommended_contracts=contracts_to_sell,
                expected_premium=expected_premium,
                premium_pct=(expected_premium / account_value) * 100,
                delta=best_call.get('delta'),
                iv=best_call.get('iv'),
                volume=best_call.get('volume'),
                open_interest=best_call.get('open_interest'),
                reason=reason,
                confidence="high" if best_score > 0.8 else "medium",
                action_type="open_covered_call"
            )
            
            recommendations.append(rec)
            
        except Exception as e:
            logger.error(f"Error generating fuzzy call recommendations: {e}")
        
        return recommendations
    
    def get_fuzzy_hedge_recommendations(
        self,
        trades: List[Trade],
        account_value: float,
        iwm_price: float,
        vix_value: Optional[float] = None
    ) -> List[TradeRecommendation]:
        """
        Get put hedge recommendations using fuzzy logic
        
        Args:
            trades: List of all trades
            account_value: Total account value
            iwm_price: Current IWM price
            vix_value: Current VIX value (optional)
            
        Returns:
            List of hedge recommendations
        """
        recommendations = []
        
        # Get fuzzy inputs
        fuzzy_inputs = get_fuzzy_inputs(
            trades, account_value, vix_value, None, {'IWM': iwm_price}
        )
        
        # Calculate hedge score
        hedge_score, hedge_otm_pct = self.fuzzy_strategy.calculate_hedge_score(
            fuzzy_inputs['vix_norm'],
            fuzzy_inputs['cycle'],
            fuzzy_inputs['trend'],
            fuzzy_inputs['stock_weight'],
            fuzzy_inputs['delta_port']
        )
        
        # Only hedge if score is significant
        if hedge_score < 0.4:
            return []
        
        # Calculate hedge notional
        stock_positions = get_current_positions(trades).get('stock', {})
        iwm_shares = stock_positions.get('IWM', 0)
        
        if iwm_shares <= 0:
            return []
        
        stock_exposure = iwm_shares * iwm_price
        hedge_notional = hedge_score * fuzzy_inputs['stock_weight'] * account_value
        hedge_notional = min(hedge_notional, stock_exposure * 0.5)  # Cap at 50% of exposure
        
        # Calculate target strike
        target_strike = iwm_price * (1 - hedge_otm_pct / 100)
        target_strike = round(target_strike * 2) / 2
        
        try:
            md_client = MarketDataClient()
            
            # Get 30 DTE puts for hedging
            puts = md_client.get_options_chain(
                symbol='IWM',
                dte_min=25,
                dte_max=35,
                option_type='put',
                strike_min=target_strike - 2.0,
                strike_max=target_strike + 2.0
            )
            
            if puts.empty:
                return []
            
            # Find put closest to target strike
            puts['strike_diff'] = abs(puts['strike'] - target_strike)
            puts = puts.sort_values('strike_diff')
            
            best_put = puts.iloc[0]
            put_price = best_put['mid']
            
            # Calculate contracts needed
            contracts_needed = max(1, int(hedge_notional / (best_put['strike'] * 100)))
            
            cost = put_price * 100 * contracts_needed
            
            expiration_date = date.today() + timedelta(days=30)
            
            reason = (
                f"🛡️ FUZZY HEDGE: score={hedge_score:.2f}, "
                f"{hedge_otm_pct:.1f}% OTM, vix_norm={fuzzy_inputs['vix_norm']:.2f}"
            )
            
            rec = TradeRecommendation(
                symbol='IWM',
                option_symbol=best_put['option_symbol'],
                strike=best_put['strike'],
                expiration=expiration_date,
                option_type='put',
                bid=best_put['bid'],
                ask=best_put['ask'],
                mid=put_price,
                recommended_price=put_price,
                recommended_contracts=contracts_needed,
                expected_premium=-cost,  # Negative = cost
                premium_pct=0,
                delta=best_put.get('delta'),
                iv=best_put.get('iv'),
                volume=best_put.get('volume'),
                open_interest=best_put.get('open_interest'),
                reason=reason,
                confidence="high" if hedge_score > 0.7 else "medium",
                action_type="hedge"
            )
            
            recommendations.append(rec)
            
        except Exception as e:
            logger.error(f"Error generating fuzzy hedge recommendations: {e}")
        
        return recommendations

