# Strategy Module
from .premium_calculator import (
    calculate_daily_target,
    calculate_contracts_needed,
    calculate_expected_premium,
    get_position_sizing_recommendation
)
from .rules import (
    TARGET_DAILY_PREMIUM_PCT,
    CLOSE_THRESHOLD,
    ROLL_PREMIUM_MIN,
    ROLL_PREMIUM_MAX,
    PREFERRED_DTE
)
from .trade_recommendations import (
    get_trade_recommendations,
    TradeRecommendation
)
from .recommendation_engine import (
    get_all_recommendations,
    RecommendationType
)
from .fuzzy_engine import (
    FuzzySet,
    FuzzyVar,
    defuzzify_centroid,
    fuzzy_and,
    fuzzy_or,
    fuzzy_not
)
from .fuzzy_strategy import FuzzyStrategy
from .fuzzy_inputs import (
    get_fuzzy_inputs,
    calculate_portfolio_metrics,
    calculate_assigned_share_metrics,
    normalize_vix,
    calculate_trend_normalized,
    calculate_cycle_normalized
)
from .fuzzy_recommendations import FuzzyRecommendationEngine
from .fuzzy_backtest import (
    FuzzyBacktestEngine,
    FuzzyBacktestParams,
    PortfolioState,
    OptionPosition,
    BacktestMetrics
)
from .fuzzy_optimizer import (
    FuzzyOptimizer,
    OptimizationResult
)

__all__ = [
    'calculate_daily_target',
    'calculate_contracts_needed',
    'calculate_expected_premium',
    'get_position_sizing_recommendation',
    'TARGET_DAILY_PREMIUM_PCT',
    'CLOSE_THRESHOLD',
    'ROLL_PREMIUM_MIN',
    'ROLL_PREMIUM_MAX',
    'PREFERRED_DTE',
    'get_trade_recommendations',
    'TradeRecommendation',
    'get_all_recommendations',
    'RecommendationType',
    'FuzzySet',
    'FuzzyVar',
    'defuzzify_centroid',
    'fuzzy_and',
    'fuzzy_or',
    'fuzzy_not',
    'FuzzyStrategy',
    'get_fuzzy_inputs',
    'calculate_portfolio_metrics',
    'calculate_assigned_share_metrics',
    'normalize_vix',
    'calculate_trend_normalized',
    'calculate_cycle_normalized',
    'FuzzyRecommendationEngine',
    'FuzzyBacktestEngine',
    'FuzzyBacktestParams',
    'PortfolioState',
    'OptionPosition',
    'BacktestMetrics',
    'FuzzyOptimizer',
    'OptimizationResult'
]



