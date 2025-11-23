"""
Fuzzy Logic Strategy for Options Trading

Implements fuzzy rules for:
1. Put selling (moneyness and size)
2. Call writing (when assigned)
3. Share to ITM call conversion
4. Put hedging
"""
from typing import Dict, Optional, Tuple
import logging
from datetime import date, timedelta

from .fuzzy_engine import FuzzySet, FuzzyVar, defuzzify_centroid, fuzzy_and, fuzzy_or, fuzzy_not

logger = logging.getLogger(__name__)


class FuzzyStrategy:
    """
    Fuzzy logic-based trading strategy
    """
    
    def __init__(self):
        """Initialize fuzzy variables and membership functions"""
        self._init_fuzzy_variables()
    
    def _init_fuzzy_variables(self):
        """Initialize all fuzzy variables with their membership functions"""
        
        # Cycle: -1 (oversold) to +1 (overbought)
        self.cycle_var = FuzzyVar("cycle", [
            FuzzySet("oversold", -1.0, -1.0, -0.4, -0.1),
            FuzzySet("neutral", -0.4, -0.1, 0.1, 0.4),
            FuzzySet("overbought", 0.1, 0.4, 1.0, 1.0),
        ])
        
        # Trend: -1 (down) to +1 (up)
        self.trend_var = FuzzyVar("trend", [
            FuzzySet("down", -1.0, -1.0, -0.3, -0.05),
            FuzzySet("flat", -0.3, -0.05, 0.05, 0.3),
            FuzzySet("up", 0.05, 0.3, 1.0, 1.0),
        ])
        
        # VIX normalized: 0 (low) to 1 (high)
        self.vix_var = FuzzyVar("vix_norm", [
            FuzzySet("low", 0.0, 0.0, 0.2, 0.4),
            FuzzySet("mid", 0.2, 0.4, 0.6, 0.8),
            FuzzySet("high", 0.6, 0.8, 1.0, 1.0),
        ])
        
        # Buying power fraction: 0 (critical) to 1 (comfortable)
        self.bp_frac_var = FuzzyVar("bp_frac", [
            FuzzySet("critical", 0.0, 0.0, 0.1, 0.2),
            FuzzySet("tight", 0.1, 0.2, 0.4, 0.5),
            FuzzySet("comfortable", 0.4, 0.5, 1.0, 1.0),
        ])
        
        # Stock weight: 0 (light) to 1 (heavy)
        self.stock_weight_var = FuzzyVar("stock_weight", [
            FuzzySet("light", 0.0, 0.0, 0.2, 0.3),
            FuzzySet("normal", 0.2, 0.3, 0.6, 0.7),
            FuzzySet("heavy", 0.6, 0.7, 1.0, 1.0),
        ])
        
        # Premium gap: 0 (met) to 1 (far below)
        self.premium_gap_var = FuzzyVar("premium_gap", [
            FuzzySet("met", 0.0, 0.0, 0.1, 0.3),
            FuzzySet("slightly_below", 0.1, 0.3, 0.5, 0.6),
            FuzzySet("far_below", 0.5, 0.6, 1.0, 1.0),
        ])
        
        # Unrealized PnL %: negative (loss) to positive (profit)
        self.unreal_pnl_var = FuzzyVar("unreal_pnl_pct", [
            FuzzySet("deep_loss", -1.0, -1.0, -0.1, -0.05),
            FuzzySet("mild_loss", -0.1, -0.05, -0.01, 0.0),
            FuzzySet("flat", -0.01, 0.0, 0.01, 0.05),
            FuzzySet("profit", 0.01, 0.05, 1.0, 1.0),
        ])
        
        # IV rank: 0 (low) to 1 (high)
        self.iv_rank_var = FuzzyVar("iv_rank", [
            FuzzySet("low", 0.0, 0.0, 0.2, 0.4),
            FuzzySet("med", 0.2, 0.4, 0.6, 0.8),
            FuzzySet("high", 0.6, 0.8, 1.0, 1.0),
        ])
        
        # Delta portfolio: normalized
        self.delta_port_var = FuzzyVar("delta_port", [
            FuzzySet("short", -1.0, -1.0, -0.3, -0.1),
            FuzzySet("neutral", -0.3, -0.1, 0.1, 0.3),
            FuzzySet("long", 0.1, 0.3, 1.0, 1.0),
        ])
        
        # Distance from breakeven: -1 (below) to +1 (above)
        self.dist_from_be_var = FuzzyVar("dist_from_be", [
            FuzzySet("below_BE", -1.0, -1.0, -0.05, 0.0),
            FuzzySet("near_BE", -0.05, 0.0, 0.05, 0.1),
            FuzzySet("above_BE", 0.05, 0.1, 1.0, 1.0),
        ])
    
    def calculate_put_moneyness(
        self,
        cycle: float,
        trend: float
    ) -> float:
        """
        Calculate put moneyness recommendation using fuzzy logic
        
        Args:
            cycle: Cycle swing value (-1 to +1)
            trend: Trend value (-1 to +1)
            
        Returns:
            Put moneyness (-3 to +3): negative = ITM, 0 = ATM, positive = OTM
        """
        cycle_mf = self.cycle_var.fuzzify(cycle)
        trend_mf = self.trend_var.fuzzify(trend)
        
        # Rule weights and output values
        weights = {}
        values = {}
        
        # Rule 1: Oversold & trend up -> slightly ITM (-1.5)
        w1 = fuzzy_and(cycle_mf["oversold"], trend_mf["up"])
        if w1 > 0:
            weights["itm"] = w1
            values["itm"] = -1.5
        
        # Rule 2: Oversold & trend down -> ATM (0)
        w2 = fuzzy_and(cycle_mf["oversold"], trend_mf["down"])
        if w2 > 0:
            weights["atm"] = w2
            values["atm"] = 0.0
        
        # Rule 3: Neutral & trend up -> slightly OTM (+0.5)
        w3 = fuzzy_and(cycle_mf["neutral"], trend_mf["up"])
        if w3 > 0:
            weights["slightly_otm"] = w3
            values["slightly_otm"] = 0.5
        
        # Rule 4: Neutral & trend down -> ATM (0)
        w4 = fuzzy_and(cycle_mf["neutral"], trend_mf["down"])
        if w4 > 0:
            if "atm" in weights:
                weights["atm"] = fuzzy_or(weights["atm"], w4)
            else:
                weights["atm"] = w4
                values["atm"] = 0.0
        
        # Rule 5: Overbought & trend up -> slightly OTM (+1)
        w5 = fuzzy_and(cycle_mf["overbought"], trend_mf["up"])
        if w5 > 0:
            weights["otm"] = w5
            values["otm"] = 1.0
        
        # Rule 6: Overbought & trend down -> OTM (+2)
        w6 = fuzzy_and(cycle_mf["overbought"], trend_mf["down"])
        if w6 > 0:
            if "otm" in weights:
                weights["otm"] = fuzzy_or(weights["otm"], w6)
                # Weighted average of +1 and +2
                values["otm"] = (w5 * 1.0 + w6 * 2.0) / (w5 + w6) if (w5 + w6) > 0 else 2.0
            else:
                weights["otm"] = w6
                values["otm"] = 2.0
        
        # Default to ATM if no rules fire
        if not weights:
            return 0.0
        
        return defuzzify_centroid(weights, values)
    
    def calculate_put_size_frac(
        self,
        premium_gap: float,
        vix_norm: float = 0.5,
        bp_frac: float = 0.5
    ) -> float:
        """
        Calculate put size fraction using fuzzy logic
        
        Args:
            premium_gap: Premium gap (0 = met, 1 = far below)
            vix_norm: Normalized VIX (0-1)
            bp_frac: Buying power fraction (0-1)
            
        Returns:
            Put size fraction (0-1): fraction of target premium to chase
        """
        gap_mf = self.premium_gap_var.fuzzify(premium_gap)
        vix_mf = self.vix_var.fuzzify(vix_norm)
        bp_mf = self.bp_frac_var.fuzzify(bp_frac)
        
        weights = {}
        values = {}
        
        # Rule 1: Premium gap far below -> large size (~1.0)
        w1 = gap_mf["far_below"]
        if w1 > 0:
            weights["large"] = w1
            values["large"] = 1.0
        
        # Rule 2: Premium gap slightly below -> medium size (~0.5)
        w2 = gap_mf["slightly_below"]
        if w2 > 0:
            weights["medium"] = w2
            values["medium"] = 0.5
        
        # Rule 3: Premium gap met -> small size (~0.2)
        w3 = gap_mf["met"]
        if w3 > 0:
            weights["small"] = w3
            values["small"] = 0.2
        
        if not weights:
            return 0.5  # Default medium
        
        result = defuzzify_centroid(weights, values)
        
        # Adjust for buying power constraints
        # If BP is critical, reduce size
        if bp_mf["critical"] > 0.5:
            result *= 0.5  # Reduce size by 50%
        elif bp_mf["tight"] > 0.5:
            result *= 0.75  # Reduce size by 25% when tight
        
        # Adjust for VIX (higher VIX = more premium available, can be more aggressive)
        if vix_mf["high"] > 0.5:
            result *= 1.2  # Increase sizes by 20%
        elif vix_mf["low"] > 0.5:
            result *= 0.9  # Slightly reduce when VIX is low
        
        return max(0.0, min(1.0, result))  # Clamp to [0, 1]
    
    def calculate_call_sell_score(
        self,
        unreal_pnl_pct: float,
        dist_from_be: float,
        iv_rank: float,
        premium_yield: float = 0.0
    ) -> float:
        """
        Calculate call sell score using fuzzy logic
        
        Args:
            unreal_pnl_pct: Unrealized PnL as % of cost basis
            dist_from_be: Distance from breakeven (call_strike - cost_basis) / cost_basis
            iv_rank: IV rank (0-1)
            premium_yield: Premium / underlying (annualized %)
            
        Returns:
            Call sell score (0-1): 0 = don't sell, 1 = definitely sell
        """
        pnl_mf = self.unreal_pnl_var.fuzzify(unreal_pnl_pct)
        be_mf = self.dist_from_be_var.fuzzify(dist_from_be)
        iv_mf = self.iv_rank_var.fuzzify(iv_rank)
        
        # Calculate loss lock risk
        loss_lock_weights = {}
        loss_lock_values = {}
        
        # Deep loss & below BE -> high risk
        w1 = fuzzy_and(pnl_mf["deep_loss"], be_mf["below_BE"])
        if w1 > 0:
            loss_lock_weights["high"] = w1
            loss_lock_values["high"] = 1.0
        
        # Small loss & near BE -> medium risk
        w2 = fuzzy_and(pnl_mf["mild_loss"], be_mf["near_BE"])
        if w2 > 0:
            loss_lock_weights["medium"] = w2
            loss_lock_values["medium"] = 0.5
        
        # Profit & above BE -> low risk
        w3 = fuzzy_and(pnl_mf["profit"], be_mf["above_BE"])
        if w3 > 0:
            loss_lock_weights["low"] = w3
            loss_lock_values["low"] = 0.0
        
        loss_lock_risk = defuzzify_centroid(loss_lock_weights, loss_lock_values) if loss_lock_weights else 0.5
        
        # Calculate premium attractiveness (simplified)
        # High IV rank & high premium yield -> attractive
        premium_attr = 0.5  # Default
        if iv_mf["high"] > 0.5 and premium_yield > 0.01:  # >1% annualized
            premium_attr = 0.8
        elif iv_mf["med"] > 0.5 and premium_yield > 0.005:  # >0.5% annualized
            premium_attr = 0.5
        elif iv_mf["low"] > 0.5 or premium_yield < 0.003:  # <0.3% annualized
            premium_attr = 0.2
        
        # Combine: high risk OR low attractiveness -> low score
        if loss_lock_risk > 0.7 or premium_attr < 0.3:
            return 0.2
        elif loss_lock_risk < 0.3 and premium_attr > 0.7:
            return 0.9
        elif loss_lock_risk < 0.3 and premium_attr >= 0.5:
            return 0.7  # Low risk with medium/high attractiveness
        elif loss_lock_risk > 0.4 and premium_attr > 0.5:
            return 0.6
        elif loss_lock_risk < 0.4 and premium_attr >= 0.5:
            return 0.65  # Medium risk with good attractiveness
        
        return 0.5  # Default medium
    
    def calculate_call_moneyness(
        self,
        cycle: float,
        trend: float
    ) -> float:
        """
        Calculate call moneyness recommendation
        
        Args:
            cycle: Cycle swing value (-1 to +1)
            trend: Trend value (-1 to +1)
            
        Returns:
            Call moneyness (0 to +5): 0 = at breakeven, higher = further OTM
        """
        cycle_mf = self.cycle_var.fuzzify(cycle)
        trend_mf = self.trend_var.fuzzify(trend)
        
        weights = {}
        values = {}
        
        # Trend up & cycle oversold -> further OTM (+3)
        w1 = fuzzy_and(trend_mf["up"], cycle_mf["oversold"])
        if w1 > 0:
            weights["far_otm"] = w1
            values["far_otm"] = 3.0
        
        # Trend up & cycle neutral -> slightly OTM (+1.5)
        w2 = fuzzy_and(trend_mf["up"], cycle_mf["neutral"])
        if w2 > 0:
            weights["otm"] = w2
            values["otm"] = 1.5
        
        # Trend down & cycle overbought -> near BE (+0.5)
        w3 = fuzzy_and(trend_mf["down"], cycle_mf["overbought"])
        if w3 > 0:
            weights["near_be"] = w3
            values["near_be"] = 0.5
        
        # Default: slightly OTM
        if not weights:
            return 1.0
        
        return defuzzify_centroid(weights, values)
    
    def calculate_convert_score(
        self,
        bp_frac: float,
        stock_weight: float,
        vix_norm: float = 0.5
    ) -> Tuple[float, float]:
        """
        Calculate share to ITM call conversion score
        
        Args:
            bp_frac: Buying power fraction (0-1)
            stock_weight: Stock weight in portfolio (0-1)
            vix_norm: Normalized VIX (0-1)
            
        Returns:
            Tuple of (convert_score, itm_depth):
            - convert_score: 0-1, fraction of shares to convert
            - itm_depth: 1-5, % ITM or delta target (0.7-0.9)
        """
        bp_mf = self.bp_frac_var.fuzzify(bp_frac)
        stock_mf = self.stock_weight_var.fuzzify(stock_weight)
        vix_mf = self.vix_var.fuzzify(vix_norm)
        
        weights = {}
        values = {}
        
        # Critical BP & heavy stock -> high conversion
        w1 = fuzzy_and(bp_mf["critical"], stock_mf["heavy"])
        if w1 > 0:
            weights["high"] = w1
            values["high"] = 0.8
        
        # Tight BP & heavy stock -> medium conversion
        w2 = fuzzy_and(bp_mf["tight"], stock_mf["heavy"])
        if w2 > 0:
            weights["medium"] = w2
            values["medium"] = 0.5
        
        # Comfortable BP OR light stock -> low conversion
        w3 = fuzzy_or(bp_mf["comfortable"], stock_mf["light"])
        if w3 > 0:
            weights["low"] = w3
            values["low"] = 0.2
        
        convert_score = defuzzify_centroid(weights, values) if weights else 0.0
        convert_score = max(0.0, min(1.0, convert_score))
        
        # ITM depth based on VIX
        # High VIX -> shallow (delta 0.7, more leverage)
        # Low VIX -> deep (delta 0.9, less time value)
        if vix_mf["high"] > 0.5:
            itm_depth = 0.7  # Delta target
        elif vix_mf["low"] > 0.5:
            itm_depth = 0.9  # Delta target
        else:
            itm_depth = 0.8  # Delta target
        
        return convert_score, itm_depth
    
    def calculate_hedge_score(
        self,
        vix_norm: float,
        cycle: float,
        trend: float,
        stock_weight: float,
        delta_port: float = 0.0
    ) -> Tuple[float, float]:
        """
        Calculate put hedge score and OTM distance
        
        Args:
            vix_norm: Normalized VIX (0-1)
            cycle: Cycle swing value (-1 to +1)
            trend: Trend value (-1 to +1)
            stock_weight: Stock weight in portfolio (0-1)
            delta_port: Portfolio delta normalized (0-1)
            
        Returns:
            Tuple of (hedge_score, hedge_otm_pct):
            - hedge_score: 0-1, how much to hedge
            - hedge_otm_pct: 0-15%, OTM distance for hedge puts
        """
        vix_mf = self.vix_var.fuzzify(vix_norm)
        cycle_mf = self.cycle_var.fuzzify(cycle)
        trend_mf = self.trend_var.fuzzify(trend)
        stock_mf = self.stock_weight_var.fuzzify(stock_weight)
        delta_mf = self.delta_port_var.fuzzify(delta_port)
        
        weights = {}
        values = {}
        
        # Low VIX & overbought & trend up -> high hedge
        w1 = fuzzy_and(vix_mf["low"], cycle_mf["overbought"], trend_mf["up"])
        if w1 > 0:
            weights["high"] = w1
            values["high"] = 0.8
        
        # Mid VIX & (heavy stock OR long delta) -> medium hedge
        w2 = fuzzy_and(
            vix_mf["mid"],
            fuzzy_or(stock_mf["heavy"], delta_mf["long"])
        )
        if w2 > 0:
            weights["medium"] = w2
            values["medium"] = 0.5
        
        # High VIX & not overbought -> low hedge (expensive)
        w3 = fuzzy_and(vix_mf["high"], fuzzy_not(cycle_mf["overbought"]))
        if w3 > 0:
            weights["low"] = w3
            values["low"] = 0.2
        
        hedge_score = defuzzify_centroid(weights, values) if weights else 0.0
        hedge_score = max(0.0, min(1.0, hedge_score))
        
        # OTM distance based on VIX
        # Low VIX -> larger OTM (10-15%, cheap)
        # High VIX -> smaller OTM (5-8%, keep closer)
        if vix_mf["low"] > 0.5:
            hedge_otm_pct = 12.0  # 12% OTM
        elif vix_mf["high"] > 0.5:
            hedge_otm_pct = 6.0  # 6% OTM
        else:
            hedge_otm_pct = 9.0  # 9% OTM
        
        return hedge_score, hedge_otm_pct

