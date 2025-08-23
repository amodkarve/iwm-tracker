import pytest
from datetime import datetime
from wheeltracker.models import Trade
from wheeltracker.calculations import cost_basis


class TestCostBasis:
    def test_all_puts_closed(self):
        """Test scenario where all puts are closed (no assignment)."""
        trades = [
            Trade(
                symbol="AAPL",
                quantity=1,
                price=5.0,  # $5 premium
                side="sell",
                timestamp=datetime.now(),
                strategy="put",
                option_type="put"
            ),
            Trade(
                symbol="AAPL",
                quantity=1,
                price=2.0,  # $2 premium to close
                side="buy",
                timestamp=datetime.now(),
                strategy="put",
                option_type="put"
            )
        ]
        
        result = cost_basis(trades)
        
        # Net premium received: ($5 - $2) * 100 = $300
        assert result['shares'] == 0  # No shares owned
        assert result['basis_without_premium'] == 0  # No stock basis
        assert result['net_premium'] == 300.0  # $300 net premium received
        assert result['basis_with_premium'] == -300.0  # Negative basis (profit)
    
    def test_puts_assigned_then_covered_calls(self):
        """Test scenario where puts are assigned, then covered calls sold."""
        trades = [
            # Sell put
            Trade(
                symbol="AAPL",
                quantity=1,
                price=5.0,  # $5 premium
                side="sell",
                timestamp=datetime.now(),
                strategy="put",
                option_type="put"
            ),
            # Put gets assigned (buy shares at strike)
            Trade(
                symbol="AAPL",
                quantity=100,
                price=150.0,  # Strike price
                side="buy",
                timestamp=datetime.now(),
                strategy="stock"  # Assignment
            ),
            # Sell covered call
            Trade(
                symbol="AAPL",
                quantity=1,
                price=3.0,  # $3 premium
                side="sell",
                timestamp=datetime.now(),
                strategy="call",
                option_type="call"
            )
        ]
        
        result = cost_basis(trades)
        
        # Own 100 shares, paid $15000, received $800 in premiums
        assert result['shares'] == 100
        assert result['basis_without_premium'] == 150.0  # $15000 / 100 shares
        assert result['net_premium'] == 800.0  # ($5 + $3) * 100 premiums received
        assert result['basis_with_premium'] == 142.0  # ($15000 - $800) / 100 shares
    
    def test_partial_exercises(self):
        """Test scenario with partial option exercises."""
        trades = [
            # Sell 2 puts
            Trade(
                symbol="AAPL",
                quantity=2,
                price=5.0,  # $5 premium each
                side="sell",
                timestamp=datetime.now(),
                strategy="put",
                option_type="put"
            ),
            # One put gets assigned
            Trade(
                symbol="AAPL",
                quantity=100,
                price=150.0,  # Strike price
                side="buy",
                timestamp=datetime.now(),
                strategy="stock"  # Assignment
            ),
            # Close the other put
            Trade(
                symbol="AAPL",
                quantity=1,
                price=2.0,  # $2 premium to close
                side="buy",
                timestamp=datetime.now(),
                strategy="put",
                option_type="put"
            )
        ]
        
        result = cost_basis(trades)
        
        # Own 100 shares, paid $15000, received $800 in premiums ($10 - $2) * 100
        assert result['shares'] == 100
        assert result['basis_without_premium'] == 150.0  # $15000 / 100 shares
        assert result['net_premium'] == 800.0  # ($10 - $2) * 100 premiums
        assert result['basis_with_premium'] == 142.0  # ($15000 - $800) / 100 shares
    
    def test_stock_only_trades(self):
        """Test scenario with only stock trades (no options)."""
        trades = [
            # Buy 100 shares
            Trade(
                symbol="AAPL",
                quantity=100,
                price=150.0,
                side="buy",
                timestamp=datetime.now(),
                strategy="stock"
            ),
            # Sell 50 shares
            Trade(
                symbol="AAPL",
                quantity=50,
                price=160.0,
                side="sell",
                timestamp=datetime.now(),
                strategy="stock"
            )
        ]
        
        result = cost_basis(trades)
        
        # Own 50 shares, basis reduced proportionally
        assert result['shares'] == 50
        assert result['basis_without_premium'] == 150.0  # $7500 / 50 shares
        assert result['net_premium'] == 0.0  # No options
        assert result['basis_with_premium'] == 150.0  # Same as without premium
    
    def test_complex_wheel_strategy(self):
        """Test a complex wheel strategy with multiple cycles."""
        trades = [
            # Sell put
            Trade(
                symbol="AAPL",
                quantity=1,
                price=5.0,
                side="sell",
                timestamp=datetime.now(),
                strategy="put",
                option_type="put"
            ),
            # Put assigned
            Trade(
                symbol="AAPL",
                quantity=100,
                price=150.0,
                side="buy",
                timestamp=datetime.now(),
                strategy="stock"
            ),
            # Sell covered call
            Trade(
                symbol="AAPL",
                quantity=1,
                price=3.0,
                side="sell",
                timestamp=datetime.now(),
                strategy="call",
                option_type="call"
            ),
            # Call assigned (shares called away)
            Trade(
                symbol="AAPL",
                quantity=100,
                price=160.0,
                side="sell",
                timestamp=datetime.now(),
                strategy="stock"
            ),
            # Sell another put
            Trade(
                symbol="AAPL",
                quantity=1,
                price=4.0,
                side="sell",
                timestamp=datetime.now(),
                strategy="put",
                option_type="put"
            )
        ]
        
        result = cost_basis(trades)
        
        # No shares owned, but received premiums and profit from stock sale
        assert result['shares'] == 0
        assert result['basis_without_premium'] == 0  # No shares
        assert result['net_premium'] == 1200.0  # ($5 + $3 + $4) * 100 premiums
        assert result['basis_with_premium'] == -2200.0  # Negative basis (profit: $1200 premiums + $1000 stock profit)
    
    def test_empty_trades(self):
        """Test with empty trade list."""
        result = cost_basis([])
        
        assert result['shares'] == 0
        assert result['basis_without_premium'] == 0
        assert result['net_premium'] == 0
        assert result['basis_with_premium'] == 0 

    def test_short_call_exercise_profit_accounting(self):
        """Test that profit/loss from sold shares is properly accounted for when a short call is exercised."""
        trades = [
            # Buy 100 shares at $150
            Trade(
                symbol="AAPL",
                quantity=100,
                price=150.0,
                side="buy",
                timestamp=datetime.now(),
                strategy="stock"
            ),
            # Sell covered call at $5 premium
            Trade(
                symbol="AAPL",
                quantity=1,
                price=5.0,  # $5 premium
                side="sell",
                timestamp=datetime.now(),
                strategy="call",
                option_type="call"
            ),
            # Call gets exercised - sell shares at $160 strike price
            Trade(
                symbol="AAPL",
                quantity=100,
                price=160.0,  # Strike price
                side="sell",
                timestamp=datetime.now(),
                strategy="assignment"  # Assignment
            ),
            # Option closing trade (buy to close the short call)
            Trade(
                symbol="AAPL",
                quantity=1,
                price=0.0,  # Zero price for assignment
                side="buy",
                timestamp=datetime.now(),
                strategy="assignment",
                option_type="call"
            )
        ]
        
        result = cost_basis(trades)
        
        # No shares remaining after assignment
        assert result['shares'] == 0
        
        # Net premium received: $5 * 100 = $500
        assert result['net_premium'] == 500.0
        
        # Profit from stock sale: (160 - 150) * 100 = $1000
        # Total profit: $500 premium + $1000 stock profit = $1500
        # Since no shares remain, basis_with_premium should reflect total profit
        assert result['basis_with_premium'] == -1500.0  # Negative because it's profit
        
        # Basis without premium should be 0 since no shares remain
        assert result['basis_without_premium'] == 0.0

    def test_short_call_exercise_loss_accounting(self):
        """Test that loss from sold shares is properly accounted for when a short call is exercised at a loss."""
        trades = [
            # Buy 100 shares at $180
            Trade(
                symbol="AAPL",
                quantity=100,
                price=180.0,
                side="buy",
                timestamp=datetime.now(),
                strategy="stock"
            ),
            # Sell covered call at $3 premium
            Trade(
                symbol="AAPL",
                quantity=1,
                price=3.0,  # $3 premium
                side="sell",
                timestamp=datetime.now(),
                strategy="call",
                option_type="call"
            ),
            # Call gets exercised - sell shares at $160 strike price (loss)
            Trade(
                symbol="AAPL",
                quantity=100,
                price=160.0,  # Strike price (below cost basis)
                side="sell",
                timestamp=datetime.now(),
                strategy="assignment"  # Assignment
            ),
            # Option closing trade (buy to close the short call)
            Trade(
                symbol="AAPL",
                quantity=1,
                price=0.0,  # Zero price for assignment
                side="buy",
                timestamp=datetime.now(),
                strategy="assignment",
                option_type="call"
            )
        ]
        
        result = cost_basis(trades)
        
        # No shares remaining after assignment
        assert result['shares'] == 0
        
        # Net premium received: $3 * 100 = $300
        assert result['net_premium'] == 300.0
        
        # Loss from stock sale: (160 - 180) * 100 = -$2000
        # Net result: $300 premium - $2000 stock loss = -$1700 loss
        # Since no shares remain, basis_with_premium should reflect total loss
        assert result['basis_with_premium'] == 1700.0  # Positive because it's a loss
        
        # Basis without premium should be 0 since no shares remain
        assert result['basis_without_premium'] == 0.0

    def test_partial_short_call_exercise(self):
        """Test partial exercise of short calls where some shares remain."""
        trades = [
            # Buy 200 shares at $150
            Trade(
                symbol="AAPL",
                quantity=200,
                price=150.0,
                side="buy",
                timestamp=datetime.now(),
                strategy="stock"
            ),
            # Sell 2 covered calls at $5 premium each
            Trade(
                symbol="AAPL",
                quantity=2,
                price=5.0,  # $5 premium per contract
                side="sell",
                timestamp=datetime.now(),
                strategy="call",
                option_type="call"
            ),
            # One call gets exercised - sell 100 shares at $160 strike price
            Trade(
                symbol="AAPL",
                quantity=100,
                price=160.0,  # Strike price
                side="sell",
                timestamp=datetime.now(),
                strategy="assignment"  # Assignment
            ),
            # Option closing trade for the exercised call
            Trade(
                symbol="AAPL",
                quantity=1,
                price=0.0,  # Zero price for assignment
                side="buy",
                timestamp=datetime.now(),
                strategy="assignment",
                option_type="call"
            )
        ]
        
        result = cost_basis(trades)
        
        # 100 shares remaining after partial assignment
        assert result['shares'] == 100
        
        # Net premium received: $5 * 2 * 100 = $1000
        assert result['net_premium'] == 1000.0
        
        # Profit from stock sale: (160 - 150) * 100 = $1000
        # Remaining shares cost basis: $150 * 100 = $15000
        # Adjusted basis with premium: $15000 - $1000 premium = $14000
        # Per share basis: $14000 / 100 = $140
        assert result['basis_with_premium'] == 140.0
        
        # Basis without premium: $15000 / 100 = $150
        assert result['basis_without_premium'] == 150.0 

    def testWheelAssignmentIwmCostBasis(self):
        """
        Test wheel-strategy accounting for an IWM position when 10 covered calls are assigned.
        
        GIVEN:
        - Initial shares: 1,500
        - Purchase price per share: $227.00
        - Total initial cost (C0): 1,500 * 227.00 = 340,500.00
        - Total option premium collected so far (P): 4,599.00
        - Covered calls sold: 10 contracts at strike 228.00 → 1,000 shares get assigned
        - Assignment proceeds (A): 1,000 * 228.00 = 228,000.00
        - Cost of assigned shares (CA): 1,000 * 227.00 = 227,000.00
        - Realized PnL from assignment on the shares only (R_assign): A - CA = 1,000.00
        - Remaining shares after assignment: 500
        - Book value of remaining shares at original cost (BV_remain): 500 * 227.00 = 113,500.00
        - Total realized cash inflows to date = P + A = 4,599.00 + 228,000.00 = 232,599.00
        - Net cash outlay remaining after inflows (should equal effective remaining cost): 
          NetOut = C0 - (P + A) = 340,500.00 - 232,599.00 = 107,901.00
        
        Effective cost basis for remaining shares:
        - EffectiveRemainingCost (ERC) = BV_remain - (P + R_assign) 
          = 113,500.00 - (4,599.00 + 1,000.00) 
          = 113,500.00 - 5,599.00 
          = 107,901.00
        - Effective average cost per remaining share (EAC) = ERC / 500 = 107,901.00 / 500 = 215.802
          *Round to cents if your system uses 2-decimal currency: 215.80*
        """
        from datetime import datetime
        
        trades = [
            # Buy 1,500 shares at $227.00
            Trade(
                symbol="IWM",
                quantity=1500,
                price=227.00,
                side="buy",
                timestamp=datetime.now(),
                strategy="stock"
            ),
            # Record total premium collected 4,599.00 (from previously sold calls)
            # This represents the cumulative premium from multiple covered call sales
            Trade(
                symbol="IWM",
                quantity=45,  # 45 contracts * 100 shares per contract = 4,500 shares
                price=1.00,  # $1.00 per share to get 4,500.00 total (45 * 100 * 1.00 = 4,500.00)
                side="sell",
                timestamp=datetime.now(),
                strategy="call",
                option_type="call"
            ),
            # Additional premium to reach 4,599.00 total
            Trade(
                symbol="IWM",
                quantity=1,  # 1 contract * 100 shares per contract = 100 shares
                price=0.99,  # $0.99 per share to get 99.00 total (1 * 100 * 0.99 = 99.00)
                side="sell",
                timestamp=datetime.now(),
                strategy="call",
                option_type="call"
            ),
            # Assign 1,000 shares at 228.00 due to covered calls (10 contracts)
            Trade(
                symbol="IWM",
                quantity=1000,
                price=228.00,  # Strike price
                side="sell",
                timestamp=datetime.now(),
                strategy="assignment"  # Assignment
            ),
            # Option closing trade for the assigned calls
            Trade(
                symbol="IWM",
                quantity=10,  # 10 contracts assigned
                price=0.0,  # Zero price for assignment
                side="buy",
                timestamp=datetime.now(),
                strategy="assignment",
                option_type="call"
            )
        ]
        
        result = cost_basis(trades, use_wheel_strategy=True)
        
        # Shares & book values
        assert result['shares'] == 500, f"Expected remaining shares: 500, got: {result['shares']}"
        assert result['basis_without_premium'] == 227.00, f"Expected avg cost without premium: 227.00, got: {result['basis_without_premium']}"
        
        # Book value of remaining shares at original cost: 500 * 227.00 = 113,500.00
        book_value_remaining = result['shares'] * result['basis_without_premium']
        assert book_value_remaining == 113500.00, f"Expected book value remaining: 113,500.00, got: {book_value_remaining}"
        
        # Realized results
        # Realized PnL from assignment (shares-only): 1,000.00
        # This is calculated as: (228.00 - 227.00) * 1000 = 1,000.00
        assignment_proceeds = 1000 * 228.00  # 228,000.00
        cost_of_assigned_shares = 1000 * 227.00  # 227,000.00
        realized_pnl_assignment = assignment_proceeds - cost_of_assigned_shares  # 1,000.00
        
        # Premium realized/collected to date: 4,599.00
        total_premium_collected = result['net_premium']
        assert total_premium_collected == 4599.00, f"Expected total premium collected: 4,599.00, got: {total_premium_collected}"
        
        # Wheel strategy accounting - include realized gains/losses in basis calculation
        # EffectiveRemainingCost (ERC) = BV_remain - (P + R_assign) = 113,500.00 - (4,599.00 + 1,000.00) = 107,901.00
        effective_remaining_cost = book_value_remaining - (total_premium_collected + realized_pnl_assignment)
        assert effective_remaining_cost == 107901.00, f"Expected effective remaining cost: 107,901.00, got: {effective_remaining_cost}"
        
        # Effective average cost per remaining share (EAC) to 3 decimals: 215.802
        effective_average_cost_per_share = effective_remaining_cost / result['shares']
        assert abs(effective_average_cost_per_share - 215.802) < 0.001, f"Expected EAC to 3 decimals: 215.802, got: {effective_average_cost_per_share}"
        
        # If code rounds to cents, EAC to 2 decimals: 215.80
        effective_average_cost_per_share_rounded = round(effective_average_cost_per_share, 2)
        assert effective_average_cost_per_share_rounded == 215.80, f"Expected EAC to 2 decimals: 215.80, got: {effective_average_cost_per_share_rounded}"
        
        # Verify the wheel strategy basis_with_premium calculation matches our expected EAC
        assert abs(result['basis_with_premium'] - effective_average_cost_per_share) < 0.001, f"Expected basis_with_premium to match EAC: {effective_average_cost_per_share}, got: {result['basis_with_premium']}"
        
        # Cash-flow consistency check
        # (initialCost) - (assignmentProceeds + premiums) == expected effective remaining cost
        # i.e., 340,500.00 - (228,000.00 + 4,599.00) == 107,901.00
        initial_cost = 1500 * 227.00  # 340,500.00
        assignment_proceeds_total = 1000 * 228.00  # 228,000.00
        cash_flow_check = initial_cost - (assignment_proceeds_total + total_premium_collected)
        expected_effective_remaining_cost = 107901.00  # From wheel strategy requirements
        assert cash_flow_check == expected_effective_remaining_cost, f"Cash flow consistency check failed: {initial_cost} - ({assignment_proceeds_total} + {total_premium_collected}) = {cash_flow_check}, expected: {expected_effective_remaining_cost}" 