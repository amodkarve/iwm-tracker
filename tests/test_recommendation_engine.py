"""
Tests for recommendation engine strike filtering logic
"""
import pytest
import sys
import os
from datetime import date, timedelta
from unittest.mock import Mock, patch
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from strategy.recommendation_engine import get_new_put_recommendations


class TestPutRecommendationStrikeFiltering:
    """Test that put recommendations filter to ATM and nearby strikes"""
    
    @patch('strategy.recommendation_engine.get_1dte_puts_near_money')
    @patch('strategy.recommendation_engine.get_iwm_price')
    def test_filters_to_atm_range(self, mock_price, mock_puts):
        """Test that put recommendations only include strikes within ±$2 of current price"""
        # Mock IWM price at $220
        mock_price.return_value = 220.0
        
        # Mock put options with various strikes
        mock_puts.return_value = pd.DataFrame([
            # Deep OTM (should be filtered out)
            {'strike': 210.0, 'mid': 0.50, 'bid': 0.45, 'ask': 0.55, 'option_symbol': 'IWM_210P'},
            # 2 strikes OTM (should be included)
            {'strike': 218.0, 'mid': 0.80, 'bid': 0.75, 'ask': 0.85, 'option_symbol': 'IWM_218P'},
            # 1 strike OTM (should be included)
            {'strike': 219.0, 'mid': 0.90, 'bid': 0.85, 'ask': 0.95, 'option_symbol': 'IWM_219P'},
            # ATM (should be included)
            {'strike': 220.0, 'mid': 1.00, 'bid': 0.95, 'ask': 1.05, 'option_symbol': 'IWM_220P'},
            # 1 strike ITM (should be included)
            {'strike': 221.0, 'mid': 1.20, 'bid': 1.15, 'ask': 1.25, 'option_symbol': 'IWM_221P'},
            # Deep ITM (should be filtered out)
            {'strike': 225.0, 'mid': 5.50, 'bid': 5.45, 'ask': 5.55, 'option_symbol': 'IWM_225P'},
        ])
        
        # Get recommendations
        recs = get_new_put_recommendations(
            iwm_price=220.0,
            trend_signal=0,
            momentum_signal=0,
            account_value=1_000_000
        )
        
        # Should only include strikes in range [218, 221]
        strikes = [rec.strike for rec in recs]
        
        # All strikes should be within ±$2 of current price
        for strike in strikes:
            assert abs(strike - 220.0) <= 2.0, f"Strike {strike} is outside ATM range"
        
        # Should NOT include deep OTM or deep ITM
        assert 210.0 not in strikes, "Deep OTM strike should be filtered out"
        assert 225.0 not in strikes, "Deep ITM strike should be filtered out"
    
    @patch('strategy.recommendation_engine.get_1dte_puts_near_money')
    @patch('strategy.recommendation_engine.get_iwm_price')
    def test_atm_strike_included(self, mock_price, mock_puts):
        """Test that ATM strike is always included"""
        mock_price.return_value = 220.0
        
        mock_puts.return_value = pd.DataFrame([
            {'strike': 220.0, 'mid': 1.00, 'bid': 0.95, 'ask': 1.05, 'option_symbol': 'IWM_220P'},
        ])
        
        recs = get_new_put_recommendations(
            iwm_price=220.0,
            trend_signal=0,
            momentum_signal=0,
            account_value=1_000_000
        )
        
        assert len(recs) > 0, "Should have at least one recommendation"
        assert 220.0 in [rec.strike for rec in recs], "ATM strike should be included"
    
    @patch('strategy.recommendation_engine.get_1dte_puts_near_money')
    @patch('strategy.recommendation_engine.get_iwm_price')
    def test_one_strike_otm_included(self, mock_price, mock_puts):
        """Test that 1 strike OTM is included"""
        mock_price.return_value = 220.0
        
        mock_puts.return_value = pd.DataFrame([
            {'strike': 219.0, 'mid': 0.90, 'bid': 0.85, 'ask': 0.95, 'option_symbol': 'IWM_219P'},
        ])
        
        recs = get_new_put_recommendations(
            iwm_price=220.0,
            trend_signal=0,
            momentum_signal=0,
            account_value=1_000_000
        )
        
        assert len(recs) > 0, "Should have at least one recommendation"
        assert 219.0 in [rec.strike for rec in recs], "1 strike OTM should be included"
    
    @patch('strategy.recommendation_engine.get_1dte_puts_near_money')
    @patch('strategy.recommendation_engine.get_iwm_price')
    def test_one_strike_itm_included(self, mock_price, mock_puts):
        """Test that 1 strike ITM is included"""
        mock_price.return_value = 220.0
        
        mock_puts.return_value = pd.DataFrame([
            {'strike': 221.0, 'mid': 1.20, 'bid': 1.15, 'ask': 1.25, 'option_symbol': 'IWM_221P'},
        ])
        
        recs = get_new_put_recommendations(
            iwm_price=220.0,
            trend_signal=0,
            momentum_signal=0,
            account_value=1_000_000
        )
        
        assert len(recs) > 0, "Should have at least one recommendation"
        assert 221.0 in [rec.strike for rec in recs], "1 strike ITM should be included"
    
    @patch('strategy.recommendation_engine.get_1dte_puts_near_money')
    @patch('strategy.recommendation_engine.get_iwm_price')
    def test_deep_otm_filtered_out(self, mock_price, mock_puts):
        """Test that deep OTM strikes are filtered out"""
        mock_price.return_value = 220.0
        
        # Only provide deep OTM strikes
        mock_puts.return_value = pd.DataFrame([
            {'strike': 210.0, 'mid': 0.30, 'bid': 0.25, 'ask': 0.35, 'option_symbol': 'IWM_210P'},
            {'strike': 215.0, 'mid': 0.50, 'bid': 0.45, 'ask': 0.55, 'option_symbol': 'IWM_215P'},
        ])
        
        recs = get_new_put_recommendations(
            iwm_price=220.0,
            trend_signal=0,
            momentum_signal=0,
            account_value=1_000_000
        )
        
        # Should return empty list since all strikes are too far OTM
        assert len(recs) == 0, "Deep OTM strikes should be filtered out"
    
    @patch('strategy.recommendation_engine.get_1dte_puts_near_money')
    @patch('strategy.recommendation_engine.get_iwm_price')
    def test_deep_itm_filtered_out(self, mock_price, mock_puts):
        """Test that deep ITM strikes are filtered out"""
        mock_price.return_value = 220.0
        
        # Only provide deep ITM strikes
        mock_puts.return_value = pd.DataFrame([
            {'strike': 225.0, 'mid': 5.50, 'bid': 5.45, 'ask': 5.55, 'option_symbol': 'IWM_225P'},
            {'strike': 230.0, 'mid': 10.50, 'bid': 10.45, 'ask': 10.55, 'option_symbol': 'IWM_230P'},
        ])
        
        recs = get_new_put_recommendations(
            iwm_price=220.0,
            trend_signal=0,
            momentum_signal=0,
            account_value=1_000_000
        )
        
        # Should return empty list since all strikes are too far ITM
        assert len(recs) == 0, "Deep ITM strikes should be filtered out"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
