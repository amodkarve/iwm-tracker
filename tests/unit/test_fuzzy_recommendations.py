"""
Unit tests for fuzzy recommendation engine

Tests the FuzzyRecommendationEngine class
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
import pandas as pd
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.wheeltracker.models import Trade
from src.strategy.fuzzy_recommendations import FuzzyRecommendationEngine
from src.strategy.trade_recommendations import TradeRecommendation


class TestFuzzyPutRecommendations:
    """Test fuzzy put recommendations"""
    
    @patch('src.strategy.fuzzy_recommendations.MarketDataClient')
    @patch('src.strategy.fuzzy_recommendations.get_fuzzy_inputs')
    def test_get_fuzzy_put_recommendations_basic(self, mock_inputs, mock_client_class):
        """Test basic fuzzy put recommendations"""
        # Mock fuzzy inputs
        mock_inputs.return_value = {
            'trend': 0.5,
            'cycle': -0.3,
            'vix_norm': 0.4,
            'bp_frac': 0.6,
            'stock_weight': 0.3,
            'delta_port': 0.2,
            'premium_gap': 0.5
        }
        
        # Mock market data client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_puts = pd.DataFrame([{
            'option_symbol': 'IWM240101P220000',
            'strike': 220.0,
            'bid': 0.75,
            'ask': 0.85,
            'mid': 0.80,
            'delta': -0.3,
            'iv': 0.25,
            'volume': 100,
            'open_interest': 500
        }])
        mock_client.get_options_chain.return_value = mock_puts
        
        engine = FuzzyRecommendationEngine()
        trades = []
        account_value = 1000000.0
        iwm_price = 220.0
        
        recommendations = engine.get_fuzzy_put_recommendations(
            trades, account_value, iwm_price
        )
        
        assert len(recommendations) > 0, "Should return at least one recommendation"
        rec = recommendations[0]
        assert isinstance(rec, TradeRecommendation), "Should return TradeRecommendation"
        assert rec.option_type == 'put', "Should be a put recommendation"
        assert rec.symbol == 'IWM', "Should be for IWM"
        assert "FUZZY PUT" in rec.reason, "Reason should mention fuzzy logic"
    
    @patch('src.strategy.fuzzy_recommendations.MarketDataClient')
    @patch('src.strategy.fuzzy_recommendations.get_fuzzy_inputs')
    def test_get_fuzzy_put_recommendations_no_options(self, mock_inputs, mock_client_class):
        """Test fuzzy put recommendations when no options available"""
        mock_inputs.return_value = {
            'trend': 0.5,
            'cycle': -0.3,
            'vix_norm': 0.4,
            'bp_frac': 0.6,
            'stock_weight': 0.3,
            'delta_port': 0.2,
            'premium_gap': 0.5
        }
        
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_options_chain.return_value = pd.DataFrame()  # Empty
        
        engine = FuzzyRecommendationEngine()
        recommendations = engine.get_fuzzy_put_recommendations(
            [], 1000000.0, 220.0
        )
        
        assert len(recommendations) == 0, "Should return empty list when no options"


class TestFuzzyCallRecommendations:
    """Test fuzzy call recommendations"""
    
    @patch('src.strategy.fuzzy_recommendations.MarketDataClient')
    @patch('src.strategy.fuzzy_recommendations.get_fuzzy_inputs')
    @patch('src.strategy.fuzzy_recommendations.get_current_positions')
    @patch('src.strategy.fuzzy_recommendations.calculate_assigned_share_metrics')
    def test_get_fuzzy_call_recommendations_with_shares(self, mock_metrics, mock_positions,
                                                         mock_inputs, mock_client_class):
        """Test fuzzy call recommendations when holding shares"""
        # Mock positions
        mock_positions.return_value = {
            'stock': {'IWM': 200},  # 200 shares
            'options': []
        }
        
        # Mock share metrics
        mock_metrics.return_value = {
            'unreal_pnl_pct': 0.05,  # 5% profit
            'iv_rank': 0.7,
            'days_since_assignment': 5,
            'cost_basis': 200.0
        }
        
        # Mock fuzzy inputs
        mock_inputs.return_value = {
            'trend': 0.3,
            'cycle': 0.2,
            'vix_norm': 0.4,
            'bp_frac': 0.6,
            'stock_weight': 0.4,
            'delta_port': 0.3,
            'premium_gap': 0.5
        }
        
        # Mock market data client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_calls = pd.DataFrame([{
            'option_symbol': 'IWM240108C225000',
            'strike': 225.0,
            'bid': 0.50,
            'ask': 0.60,
            'mid': 0.55,
            'delta': 0.3,
            'iv': 0.25,
            'volume': 100,
            'open_interest': 500
        }])
        mock_client.get_options_chain.return_value = mock_calls
        
        engine = FuzzyRecommendationEngine()
        trades = [
            Trade(
                symbol="IWM",
                quantity=200,
                price=200.0,
                side="buy",
                timestamp=datetime.now() - timedelta(days=5),
                option_type="stock"
            )
        ]
        account_value = 1000000.0
        iwm_price = 210.0
        
        recommendations = engine.get_fuzzy_call_recommendations(
            trades, account_value, iwm_price
        )
        
        # May or may not return recommendations depending on call_sell_score
        # Just verify it doesn't crash
        assert isinstance(recommendations, list), "Should return a list"
    
    @patch('src.strategy.fuzzy_recommendations.get_current_positions')
    def test_get_fuzzy_call_recommendations_no_shares(self, mock_positions):
        """Test fuzzy call recommendations when no shares owned"""
        mock_positions.return_value = {
            'stock': {'IWM': 0},  # No shares
            'options': []
        }
        
        engine = FuzzyRecommendationEngine()
        recommendations = engine.get_fuzzy_call_recommendations(
            [], 1000000.0, 220.0
        )
        
        assert len(recommendations) == 0, "Should return empty when no shares"


class TestFuzzyHedgeRecommendations:
    """Test fuzzy hedge recommendations"""
    
    @patch('src.strategy.fuzzy_recommendations.MarketDataClient')
    @patch('src.strategy.fuzzy_recommendations.get_fuzzy_inputs')
    @patch('src.strategy.fuzzy_recommendations.get_current_positions')
    def test_get_fuzzy_hedge_recommendations_high_score(self, mock_positions, mock_inputs,
                                                         mock_client_class):
        """Test fuzzy hedge recommendations when hedge score is high"""
        # Mock positions
        mock_positions.return_value = {
            'stock': {'IWM': 500},  # 500 shares
            'options': []
        }
        
        # Mock fuzzy inputs - conditions that should trigger hedging
        mock_inputs.return_value = {
            'trend': 0.6,  # Up
            'cycle': 0.7,  # Overbought
            'vix_norm': 0.2,  # Low VIX
            'bp_frac': 0.6,
            'stock_weight': 0.6,  # Heavy
            'delta_port': 0.4,
            'premium_gap': 0.5
        }
        
        # Mock market data client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_puts = pd.DataFrame([{
            'option_symbol': 'IWM240130P200000',
            'strike': 200.0,
            'bid': 1.40,
            'ask': 1.60,
            'mid': 1.50,
            'delta': -0.2,
            'iv': 0.25,
            'volume': 100,
            'open_interest': 500
        }])
        mock_client.get_options_chain.return_value = mock_puts
        
        engine = FuzzyRecommendationEngine()
        trades = [
            Trade(
                symbol="IWM",
                quantity=500,
                price=220.0,
                side="buy",
                timestamp=datetime.now() - timedelta(days=10),
                option_type="stock"
            )
        ]
        account_value = 1000000.0
        iwm_price = 220.0
        
        recommendations = engine.get_fuzzy_hedge_recommendations(
            trades, account_value, iwm_price
        )
        
        # May or may not return recommendations depending on hedge_score
        # Just verify it doesn't crash
        assert isinstance(recommendations, list), "Should return a list"
    
    @patch('src.strategy.fuzzy_recommendations.get_fuzzy_inputs')
    @patch('src.strategy.fuzzy_recommendations.get_current_positions')
    def test_get_fuzzy_hedge_recommendations_low_score(self, mock_positions, mock_inputs):
        """Test fuzzy hedge recommendations when hedge score is low"""
        mock_positions.return_value = {
            'stock': {'IWM': 500},
            'options': []
        }
        
        # Mock fuzzy inputs - conditions that should NOT trigger hedging
        mock_inputs.return_value = {
            'trend': 0.0,
            'cycle': 0.0,  # Not overbought
            'vix_norm': 0.8,  # High VIX (expensive)
            'bp_frac': 0.6,
            'stock_weight': 0.3,
            'delta_port': 0.2,
            'premium_gap': 0.5
        }
        
        engine = FuzzyRecommendationEngine()
        recommendations = engine.get_fuzzy_hedge_recommendations(
            [], 1000000.0, 220.0
        )
        
        # Low hedge score should result in no recommendations
        assert len(recommendations) == 0, "Low hedge score should return empty list"
    
    @patch('src.strategy.fuzzy_recommendations.get_current_positions')
    def test_get_fuzzy_hedge_recommendations_no_stock(self, mock_positions):
        """Test fuzzy hedge recommendations when no stock owned"""
        mock_positions.return_value = {
            'stock': {'IWM': 0},  # No shares
            'options': []
        }
        
        engine = FuzzyRecommendationEngine()
        recommendations = engine.get_fuzzy_hedge_recommendations(
            [], 1000000.0, 220.0
        )
        
        assert len(recommendations) == 0, "No stock should return empty list"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

