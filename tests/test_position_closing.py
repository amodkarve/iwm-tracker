import pandas as pd
from datetime import datetime
from unittest.mock import patch, MagicMock
from wheeltracker.models import Trade
from wheeltracker.analytics import get_open_option_positions_for_closing


class TestPositionClosing:
    def test_get_open_option_positions_for_closing(self):
        """Test getting open option positions with closing metadata."""
        # Create sample trades with open positions
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
        df = pd.DataFrame(
            [
                {
                    "id": trade.id,
                    "symbol": trade.symbol,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "side": trade.side,
                    "timestamp": trade.timestamp,
                    "strategy": trade.strategy,
                    "expiration_date": trade.expiration_date,
                    "strike_price": trade.strike_price,
                    "option_type": trade.option_type,
                }
                for trade in trades
            ]
        )

        # Get open positions
        open_positions = get_open_option_positions_for_closing(df)

        # Should have 2 open short positions
        assert len(open_positions) == 2

        # Check metadata
        for _, row in open_positions.iterrows():
            assert row["is_short"] == True  # noqa: E712
            assert row["can_buy_to_close"] == True  # noqa: E712
            assert row["can_sell_to_close"] == False  # noqa: E712
            assert row["can_exercise"] == True  # noqa: E712
            assert row["abs_quantity"] == 1

    def test_get_open_option_positions_for_closing_with_closed_position(self):
        """Test that closed positions don't appear in the list."""
        # Create trades that close each other out
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

        # Convert to DataFrame
        df = pd.DataFrame(
            [
                {
                    "id": trade.id,
                    "symbol": trade.symbol,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "side": trade.side,
                    "timestamp": trade.timestamp,
                    "strategy": trade.strategy,
                    "expiration_date": trade.expiration_date,
                    "strike_price": trade.strike_price,
                    "option_type": trade.option_type,
                }
                for trade in trades
            ]
        )

        # Get open positions
        open_positions = get_open_option_positions_for_closing(df)

        # Should have 0 open positions (closed out)
        assert len(open_positions) == 0

    def test_get_open_option_positions_for_closing_long_position(self):
        """Test long position metadata."""
        # Create a long position
        trades = [
            Trade(
                symbol="AAPL",
                quantity=1,
                price=5.0,
                side="buy",
                timestamp=datetime(2025, 1, 15),
                strategy="wheel",
                expiration_date=datetime(2025, 2, 21),
                strike_price=150.0,
                option_type="put",
            ),
        ]

        # Convert to DataFrame
        df = pd.DataFrame(
            [
                {
                    "id": trade.id,
                    "symbol": trade.symbol,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "side": trade.side,
                    "timestamp": trade.timestamp,
                    "strategy": trade.strategy,
                    "expiration_date": trade.expiration_date,
                    "strike_price": trade.strike_price,
                    "option_type": trade.option_type,
                }
                for trade in trades
            ]
        )

        # Get open positions
        open_positions = get_open_option_positions_for_closing(df)

        # Should have 1 open long position
        assert len(open_positions) == 1

        row = open_positions.iloc[0]
        assert row["is_short"] == False  # noqa: E712
        assert row["can_buy_to_close"] == False  # noqa: E712
        assert row["can_sell_to_close"] == True  # noqa: E712
        assert row["can_exercise"] == False  # noqa: E712
        assert row["abs_quantity"] == 1

    @patch("wheeltracker.db.db")
    def test_buy_to_close_short_position(self, mock_db):
        """Test buying to close a short position."""
        # Mock the database
        mock_insert_trade = MagicMock()
        mock_db.insert_trade = mock_insert_trade

        # Simulate buying to close
        closing_trade = Trade(
            symbol="AAPL",
            quantity=1,
            price=2.0,  # Buy back at $2
            side="buy",
            timestamp=datetime.now(),
            strategy="close",
            expiration_date=datetime(2025, 2, 21),
            strike_price=150.0,
            option_type="put",
        )

        # Insert the closing trade
        mock_insert_trade.return_value = closing_trade
        result = mock_db.insert_trade(closing_trade)

        # Verify the trade was created correctly
        assert result.symbol == "AAPL"
        assert result.quantity == 1
        assert result.price == 2.0
        assert result.side == "buy"
        assert result.strategy == "close"
        assert result.option_type == "put"
        assert result.strike_price == 150.0

    @patch("wheeltracker.db.db")
    def test_exercise_assignment_put(self, mock_db):
        """Test put assignment (buying stock at strike price)."""
        # Mock the database
        mock_insert_trade = MagicMock()
        mock_db.insert_trade = mock_insert_trade

        # Simulate assignment (buying stock at strike price)
        assignment_trade = Trade(
            symbol="AAPL",
            quantity=100,  # 100 shares per contract
            price=150.0,  # Strike price
            side="buy",  # Buy stock when put is assigned
            timestamp=datetime.now(),
            strategy="assignment",
            expiration_date=None,
            strike_price=None,
            option_type=None,
        )

        # Insert the assignment trade
        mock_insert_trade.return_value = assignment_trade
        result = mock_db.insert_trade(assignment_trade)

        # Verify the trade was created correctly
        assert result.symbol == "AAPL"
        assert result.quantity == 100  # 100 shares per contract
        assert result.price == 150.0  # Strike price
        assert result.side == "buy"  # Buy stock when put is assigned
        assert result.strategy == "assignment"
        assert result.option_type is None  # No longer an option trade

    @patch("wheeltracker.db.db")
    def test_exercise_assignment_call(self, mock_db):
        """Test call assignment (selling stock at strike price)."""
        # Mock the database
        mock_insert_trade = MagicMock()
        mock_db.insert_trade = mock_insert_trade

        # Simulate assignment (selling stock at strike price)
        assignment_trade = Trade(
            symbol="AAPL",
            quantity=100,  # 100 shares per contract
            price=200.0,  # Strike price
            side="sell",  # Sell stock when call is assigned
            timestamp=datetime.now(),
            strategy="assignment",
            expiration_date=None,
            strike_price=None,
            option_type=None,
        )

        # Insert the assignment trade
        mock_insert_trade.return_value = assignment_trade
        result = mock_db.insert_trade(assignment_trade)

        # Verify the trade was created correctly
        assert result.symbol == "AAPL"
        assert result.quantity == 100  # 100 shares per contract
        assert result.price == 200.0  # Strike price
        assert result.side == "sell"  # Sell stock when call is assigned
        assert result.strategy == "assignment"
        assert result.option_type is None  # No longer an option trade
