import pandas as pd
from datetime import datetime
from wheeltracker.models import Trade
from wheeltracker.analytics import (
    trades_to_dataframe,
    monthly_net_premium,
    cumulative_net_premium,
    open_option_obligations,
)


class TestAnalytics:
    def test_monthly_net_premium(self):
        """Test that monthly_net_premium returns expected Series."""
        # Create sample trades
        trades = [
            Trade(
                symbol="AAPL",
                quantity=1,
                price=5.0,
                side="sell",
                timestamp=datetime(2025, 1, 15),
                strategy="wheel",
                expiration_date=datetime(2025, 2, 21),
                strike_price=150.0,
                option_type="put",
            ),
            Trade(
                symbol="AAPL",
                quantity=1,
                price=2.0,
                side="buy",
                timestamp=datetime(2025, 1, 20),
                strategy="wheel",
                expiration_date=datetime(2025, 2, 21),
                strike_price=150.0,
                option_type="put",
            ),
            Trade(
                symbol="TSLA",
                quantity=1,
                price=3.0,
                side="sell",
                timestamp=datetime(2025, 2, 10),
                strategy="wheel",
                expiration_date=datetime(2025, 3, 21),
                strike_price=200.0,
                option_type="call",
            ),
        ]

        # Convert to DataFrame
        df = trades_to_dataframe(trades)

        # Calculate monthly net premium
        monthly_premium = monthly_net_premium(df)

        # Expected results:
        # Jan 2025: +$500 (sell put) - $200 (buy put) = +$300
        # Feb 2025: +$300 (sell call) = +$300
        expected_months = pd.PeriodIndex(["2025-01", "2025-02"], freq="M")
        expected_values = [300.0, 300.0]
        expected_series = pd.Series(
            expected_values, index=expected_months, name="premium"
        )

        # Compare values and index, ignore name differences
        pd.testing.assert_series_equal(
            monthly_premium.reset_index(drop=True),
            expected_series.reset_index(drop=True),
        )

    def test_monthly_net_premium_empty_data(self):
        """Test monthly_net_premium with empty data."""
        df = pd.DataFrame()
        result = monthly_net_premium(df)
        assert result.empty

    def test_monthly_net_premium_no_options(self):
        """Test monthly_net_premium with no option trades."""
        trades = [
            Trade(
                symbol="AAPL",
                quantity=100,
                price=150.0,
                side="buy",
                timestamp=datetime(2025, 1, 15),
                strategy="stock",
                # No option details
            )
        ]

        df = trades_to_dataframe(trades)
        result = monthly_net_premium(df)
        assert result.empty

    def test_cumulative_net_premium(self):
        """Test cumulative net premium calculation."""
        trades = [
            Trade(
                symbol="AAPL",
                quantity=1,
                price=5.0,
                side="sell",
                timestamp=datetime(2025, 1, 15),
                strategy="wheel",
                expiration_date=datetime(2025, 2, 21),
                strike_price=150.0,
                option_type="put",
            ),
            Trade(
                symbol="AAPL",
                quantity=1,
                price=2.0,
                side="buy",
                timestamp=datetime(2025, 1, 20),
                strategy="wheel",
                expiration_date=datetime(2025, 2, 21),
                strike_price=150.0,
                option_type="put",
            ),
        ]

        df = trades_to_dataframe(trades)
        result = cumulative_net_premium(df)

        # Should have 2 rows with cumulative values
        assert len(result) == 2
        assert "timestamp" in result.columns
        assert "cumulative_premium" in result.columns
        assert result["cumulative_premium"].iloc[-1] == 300.0  # Final cumulative value

    def test_open_option_obligations(self):
        """Test open option obligations calculation."""
        trades = [
            Trade(
                symbol="AAPL",
                quantity=1,
                price=5.0,
                side="sell",
                timestamp=datetime(2025, 1, 15),
                strategy="wheel",
                expiration_date=datetime(2025, 2, 21),
                strike_price=150.0,
                option_type="put",
            ),
            Trade(
                symbol="AAPL",
                quantity=1,
                price=2.0,
                side="buy",
                timestamp=datetime(2025, 1, 20),
                strategy="wheel",
                expiration_date=datetime(2025, 2, 21),
                strike_price=150.0,
                option_type="put",
            ),
            Trade(
                symbol="TSLA",
                quantity=1,
                price=3.0,
                side="sell",
                timestamp=datetime(2025, 2, 10),
                strategy="wheel",
                expiration_date=datetime(2025, 3, 21),
                strike_price=200.0,
                option_type="call",
            ),
        ]

        df = trades_to_dataframe(trades)
        result = open_option_obligations(df)

        # Should have 2 open positions:
        # 1. AAPL 150 put: -1 (sold 1, bought 1) = 0 (closed)
        # 2. TSLA 200 call: -1 (sold 1, no buy) = -1 (open short)
        assert len(result) == 1
        assert result.iloc[0]["symbol"] == "TSLA"
        assert result.iloc[0]["strike_price"] == 200.0
        assert result.iloc[0]["option_type"] == "call"
        assert result.iloc[0]["net_quantity"] == -1

    def test_trades_to_dataframe(self):
        """Test converting trades to DataFrame."""
        trades = [
            Trade(
                symbol="AAPL",
                quantity=100,
                price=150.0,
                side="buy",
                timestamp=datetime(2025, 1, 15),
                strategy="stock",
            )
        ]

        df = trades_to_dataframe(trades)

        assert len(df) == 1
        assert df.iloc[0]["symbol"] == "AAPL"
        assert df.iloc[0]["quantity"] == 100
        assert df.iloc[0]["price"] == 150.0
        assert df.iloc[0]["side"] == "buy"
        assert df.iloc[0]["strategy"] == "stock"
        assert pd.isna(df.iloc[0]["option_type"])
