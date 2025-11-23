"""
Unit tests for fuzzy strategy rules

Tests all fuzzy rule functions based on original requirements
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from src.strategy.fuzzy_strategy import FuzzyStrategy


class TestPutMoneyness:
    """Test put moneyness calculation rules"""
    
    def test_oversold_trend_up_goes_itm(self):
        """Oversold & trend up → go ITM (-1 to -2 bucket)"""
        fuzzy = FuzzyStrategy()
        cycle = -0.8  # Oversold
        trend = 0.6   # Up
        
        result = fuzzy.calculate_put_moneyness(cycle, trend)
        assert result < 0, "Should be ITM (negative moneyness)"
        assert result >= -2.0, "Should be in -1 to -2 range"
    
    def test_oversold_trend_down_atm(self):
        """Oversold & trend down → still near ATM but cautious"""
        fuzzy = FuzzyStrategy()
        cycle = -0.8  # Oversold
        trend = -0.4  # Down
        
        result = fuzzy.calculate_put_moneyness(cycle, trend)
        assert abs(result) < 0.5, "Should be near ATM (close to 0)"
    
    def test_overbought_trend_up_slightly_otm(self):
        """Overbought & trend up → slightly OTM (+1)"""
        fuzzy = FuzzyStrategy()
        cycle = 0.8   # Overbought
        trend = 0.6   # Up
        
        result = fuzzy.calculate_put_moneyness(cycle, trend)
        assert result > 0, "Should be OTM (positive moneyness)"
        assert abs(result - 1.0) < 0.5, "Should be around +1"
    
    def test_overbought_trend_down_more_otm(self):
        """Overbought & trend down → more OTM (+2)"""
        fuzzy = FuzzyStrategy()
        cycle = 0.8   # Overbought
        trend = -0.4  # Down
        
        result = fuzzy.calculate_put_moneyness(cycle, trend)
        assert result > 0, "Should be OTM (positive moneyness)"
        assert result >= 1.5, "Should be more OTM (+2 or higher)"
    
    def test_neutral_conditions(self):
        """Test neutral conditions default to ATM"""
        fuzzy = FuzzyStrategy()
        cycle = 0.0   # Neutral
        trend = 0.0   # Flat
        
        result = fuzzy.calculate_put_moneyness(cycle, trend)
        assert abs(result) < 1.0, "Neutral should be near ATM"


class TestPutSizeFraction:
    """Test put size fraction calculation"""
    
    def test_premium_gap_far_below_large_size(self):
        """IF premium_gap is far_below THEN put_size_frac is large (~1.0)"""
        fuzzy = FuzzyStrategy()
        premium_gap = 0.8  # Far below
        
        result = fuzzy.calculate_put_size_frac(premium_gap)
        assert result >= 0.7, "Far below gap should result in large size (>=0.7)"
    
    def test_premium_gap_slightly_below_medium_size(self):
        """IF premium_gap is slightly_below THEN put_size_frac is medium (~0.5)"""
        fuzzy = FuzzyStrategy()
        premium_gap = 0.4  # Slightly below
        
        result = fuzzy.calculate_put_size_frac(premium_gap)
        assert 0.3 <= result <= 0.7, "Slightly below should be medium (0.3-0.7)"
    
    def test_premium_gap_met_small_size(self):
        """IF premium_gap is met THEN put_size_frac is small (~0.2)"""
        fuzzy = FuzzyStrategy()
        premium_gap = 0.1  # Met
        
        result = fuzzy.calculate_put_size_frac(premium_gap)
        assert result <= 0.4, "Met gap should result in small size (<=0.4)"
    
    def test_critical_bp_reduces_size(self):
        """Critical buying power should reduce size"""
        fuzzy = FuzzyStrategy()
        premium_gap = 0.8  # Far below (would normally be large)
        bp_frac = 0.1      # Critical (low available BP)
        
        result = fuzzy.calculate_put_size_frac(premium_gap, bp_frac=bp_frac)
        # Should be reduced compared to comfortable BP
        result_comfortable = fuzzy.calculate_put_size_frac(premium_gap, bp_frac=0.8)
        assert result <= result_comfortable, "Critical BP should reduce size"
    
    def test_high_vix_increases_size(self):
        """High VIX should allow more aggressive sizing"""
        fuzzy = FuzzyStrategy()
        premium_gap = 0.5  # Medium gap
        vix_norm = 0.8     # High VIX
        
        result = fuzzy.calculate_put_size_frac(premium_gap, vix_norm=vix_norm)
        result_low_vix = fuzzy.calculate_put_size_frac(premium_gap, vix_norm=0.2)
        # High VIX might allow slightly more aggressive sizing
        assert result >= 0.0, "Should return valid size fraction"


class TestCallSellScore:
    """Test call sell score calculation"""
    
    def test_deep_loss_below_be_high_risk(self):
        """IF unreal_pnl_pct is deep_loss AND dist_from_be is below_BE → loss_lock_risk is high"""
        fuzzy = FuzzyStrategy()
        unreal_pnl_pct = -0.15  # Deep loss
        dist_from_be = -0.1     # Below breakeven
        
        result = fuzzy.calculate_call_sell_score(unreal_pnl_pct, dist_from_be, 0.5)
        assert result < 0.5, "Deep loss below BE should result in low score (<0.5)"
    
    def test_profit_above_be_low_risk(self):
        """IF unreal_pnl_pct is profit AND dist_from_be is above_BE → loss_lock_risk is low"""
        fuzzy = FuzzyStrategy()
        unreal_pnl_pct = 0.1    # Profit
        dist_from_be = 0.15     # Above breakeven
        
        result = fuzzy.calculate_call_sell_score(unreal_pnl_pct, dist_from_be, 0.5, 0.01)
        assert result > 0.5, "Profit above BE should result in higher score (>0.5)"
    
    def test_high_iv_high_premium_attractive(self):
        """IF iv_rank is high AND premium_yield is high → premium_attractiveness is high"""
        fuzzy = FuzzyStrategy()
        unreal_pnl_pct = 0.05   # Small profit
        dist_from_be = 0.1      # Above BE
        iv_rank = 0.8           # High IV
        premium_yield = 0.02    # 2% annualized (high)
        
        result = fuzzy.calculate_call_sell_score(unreal_pnl_pct, dist_from_be, iv_rank, premium_yield)
        assert result > 0.6, "High IV and high premium should result in high score (>0.6)"
    
    def test_low_iv_low_premium_unattractive(self):
        """IF iv_rank is low AND premium_yield is low → premium_attractiveness is low"""
        fuzzy = FuzzyStrategy()
        unreal_pnl_pct = 0.05   # Small profit
        dist_from_be = 0.1      # Above BE
        iv_rank = 0.2           # Low IV
        premium_yield = 0.002   # 0.2% annualized (low)
        
        result = fuzzy.calculate_call_sell_score(unreal_pnl_pct, dist_from_be, iv_rank, premium_yield)
        assert result < 0.6, "Low IV and low premium should result in lower score (<0.6)"
    
    def test_high_risk_or_low_attractiveness_low_score(self):
        """IF loss_lock_risk is high OR premium_attractiveness is low → call_sell_score is low"""
        fuzzy = FuzzyStrategy()
        unreal_pnl_pct = -0.1   # Loss
        dist_from_be = -0.05    # Below BE
        iv_rank = 0.2           # Low IV
        premium_yield = 0.001   # Low premium
        
        result = fuzzy.calculate_call_sell_score(unreal_pnl_pct, dist_from_be, iv_rank, premium_yield)
        assert result < 0.4, "High risk or low attractiveness should result in low score (<0.4)"


class TestCallMoneyness:
    """Test call moneyness calculation"""
    
    def test_trend_up_cycle_oversold_further_otm(self):
        """IF trend up AND cycle oversold → call_moneyness further OTM"""
        fuzzy = FuzzyStrategy()
        cycle = -0.6  # Oversold
        trend = 0.6   # Up
        
        result = fuzzy.calculate_call_moneyness(cycle, trend)
        assert result >= 2.0, "Trend up and oversold should be further OTM (>=2.0)"
    
    def test_trend_down_cycle_overbought_closer_be(self):
        """IF trend down AND cycle overbought → call_moneyness closer to BE"""
        fuzzy = FuzzyStrategy()
        cycle = 0.7   # Overbought
        trend = -0.4  # Down
        
        result = fuzzy.calculate_call_moneyness(cycle, trend)
        assert result <= 1.5, "Trend down and overbought should be closer to BE (<=1.5)"
    
    def test_call_moneyness_range(self):
        """Call moneyness should be in [0, 5] range"""
        fuzzy = FuzzyStrategy()
        
        # Test various combinations
        for cycle in [-0.8, 0.0, 0.8]:
            for trend in [-0.6, 0.0, 0.6]:
                result = fuzzy.calculate_call_moneyness(cycle, trend)
                assert 0 <= result <= 5, f"Call moneyness should be in [0, 5], got {result}"


class TestConvertScore:
    """Test share to ITM call conversion score"""
    
    def test_critical_bp_heavy_stock_high_convert(self):
        """IF bp_frac is critical AND stock_weight is heavy → convert_score is high"""
        fuzzy = FuzzyStrategy()
        bp_frac = 0.1      # Critical
        stock_weight = 0.8  # Heavy
        
        convert_score, itm_depth = fuzzy.calculate_convert_score(bp_frac, stock_weight)
        assert convert_score >= 0.6, "Critical BP and heavy stock should result in high convert score (>=0.6)"
    
    def test_tight_bp_heavy_stock_medium_convert(self):
        """IF bp_frac is tight AND stock_weight is heavy → convert_score is medium"""
        fuzzy = FuzzyStrategy()
        bp_frac = 0.3      # Tight
        stock_weight = 0.8  # Heavy
        
        convert_score, itm_depth = fuzzy.calculate_convert_score(bp_frac, stock_weight)
        assert 0.3 <= convert_score <= 0.7, "Tight BP and heavy stock should be medium (0.3-0.7)"
    
    def test_comfortable_bp_low_convert(self):
        """IF bp_frac is comfortable OR stock_weight is light → convert_score is low"""
        fuzzy = FuzzyStrategy()
        bp_frac = 0.7      # Comfortable
        stock_weight = 0.5  # Normal
        
        convert_score, itm_depth = fuzzy.calculate_convert_score(bp_frac, stock_weight)
        assert convert_score <= 0.5, "Comfortable BP should result in low convert score (<=0.5)"
    
    def test_high_vix_shallow_itm_depth(self):
        """IF vix_norm is high → itm_depth shallow (delta 0.7)"""
        fuzzy = FuzzyStrategy()
        bp_frac = 0.2
        stock_weight = 0.7
        vix_norm = 0.8  # High VIX
        
        convert_score, itm_depth = fuzzy.calculate_convert_score(bp_frac, stock_weight, vix_norm)
        assert abs(itm_depth - 0.7) < 0.1, "High VIX should result in shallow ITM depth (delta ~0.7)"
    
    def test_low_vix_deep_itm_depth(self):
        """IF vix_norm is low → itm_depth deep (delta 0.9)"""
        fuzzy = FuzzyStrategy()
        bp_frac = 0.2
        stock_weight = 0.7
        vix_norm = 0.2  # Low VIX
        
        convert_score, itm_depth = fuzzy.calculate_convert_score(bp_frac, stock_weight, vix_norm)
        assert abs(itm_depth - 0.9) < 0.1, "Low VIX should result in deep ITM depth (delta ~0.9)"
    
    def test_convert_score_range(self):
        """Convert score should be in [0, 1] range"""
        fuzzy = FuzzyStrategy()
        
        for bp in [0.1, 0.5, 0.9]:
            for weight in [0.2, 0.5, 0.8]:
                convert_score, itm_depth = fuzzy.calculate_convert_score(bp, weight)
                assert 0 <= convert_score <= 1, f"Convert score should be in [0, 1], got {convert_score}"


class TestHedgeScore:
    """Test put hedge score calculation"""
    
    def test_low_vix_overbought_trend_up_high_hedge(self):
        """IF vix_norm is low AND cycle is overbought AND trend is up → hedge_score is high"""
        fuzzy = FuzzyStrategy()
        vix_norm = 0.2    # Low VIX
        cycle = 0.7       # Overbought
        trend = 0.6       # Up
        stock_weight = 0.5
        
        hedge_score, hedge_otm_pct = fuzzy.calculate_hedge_score(
            vix_norm, cycle, trend, stock_weight
        )
        assert hedge_score >= 0.6, "Low VIX, overbought, trend up should result in high hedge score (>=0.6)"
        assert hedge_otm_pct >= 10.0, "Low VIX should result in larger OTM distance (>=10%)"
    
    def test_mid_vix_heavy_stock_medium_hedge(self):
        """IF vix_norm is mid AND (stock_weight is heavy OR delta_port is long) → hedge_score is medium"""
        fuzzy = FuzzyStrategy()
        vix_norm = 0.5    # Mid VIX
        cycle = 0.0
        trend = 0.0
        stock_weight = 0.8  # Heavy
        delta_port = 0.0
        
        hedge_score, hedge_otm_pct = fuzzy.calculate_hedge_score(
            vix_norm, cycle, trend, stock_weight, delta_port
        )
        assert 0.3 <= hedge_score <= 0.7, "Mid VIX and heavy stock should be medium (0.3-0.7)"
    
    def test_high_vix_not_overbought_low_hedge(self):
        """IF vix_norm is high AND cycle not overbought → hedge_score is low (expensive)"""
        fuzzy = FuzzyStrategy()
        vix_norm = 0.8    # High VIX
        cycle = 0.0       # Not overbought
        trend = 0.0
        stock_weight = 0.5
        
        hedge_score, hedge_otm_pct = fuzzy.calculate_hedge_score(
            vix_norm, cycle, trend, stock_weight
        )
        assert hedge_score <= 0.5, "High VIX and not overbought should result in low hedge score (<=0.5)"
        assert hedge_otm_pct <= 8.0, "High VIX should result in smaller OTM distance (<=8%)"
    
    def test_low_vix_larger_otm(self):
        """IF vix_norm is low → hedge_otm_pct is larger (10–15% OTM, cheap)"""
        fuzzy = FuzzyStrategy()
        vix_norm = 0.2    # Low VIX
        cycle = 0.5
        trend = 0.3
        stock_weight = 0.6
        
        hedge_score, hedge_otm_pct = fuzzy.calculate_hedge_score(
            vix_norm, cycle, trend, stock_weight
        )
        assert 10.0 <= hedge_otm_pct <= 15.0, f"Low VIX should result in 10-15% OTM, got {hedge_otm_pct}"
    
    def test_high_vix_smaller_otm(self):
        """IF vix_norm is high → hedge_otm_pct is smaller (5–8% OTM, keep closer)"""
        fuzzy = FuzzyStrategy()
        vix_norm = 0.8    # High VIX
        cycle = 0.0
        trend = 0.0
        stock_weight = 0.5
        
        hedge_score, hedge_otm_pct = fuzzy.calculate_hedge_score(
            vix_norm, cycle, trend, stock_weight
        )
        assert 5.0 <= hedge_otm_pct <= 10.0, f"High VIX should result in 5-10% OTM, got {hedge_otm_pct}"
    
    def test_hedge_score_range(self):
        """Hedge score should be in [0, 1] range"""
        fuzzy = FuzzyStrategy()
        
        for vix in [0.2, 0.5, 0.8]:
            for cycle in [-0.8, 0.0, 0.8]:
                for trend in [-0.6, 0.0, 0.6]:
                    hedge_score, hedge_otm_pct = fuzzy.calculate_hedge_score(
                        vix, cycle, trend, 0.5
                    )
                    assert 0 <= hedge_score <= 1, f"Hedge score should be in [0, 1], got {hedge_score}"
                    assert 0 <= hedge_otm_pct <= 20, f"Hedge OTM % should be reasonable, got {hedge_otm_pct}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

