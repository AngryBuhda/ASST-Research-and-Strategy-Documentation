
"""
ASST Aggressive Volatility Arbitrage Model
Technical Implementation for Share Accumulation & Premium Compounding
Author: Quantitative Strategy Team
Date: September 27, 2025
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class ASSTPremiumCompounder:
    """
    Comprehensive volatility arbitrage model for ASST share accumulation
    Implements Kelly Criterion position sizing with premium compounding
    """

    def __init__(self, current_price=2.40, monthly_capital=4000, 
                 initial_portfolio=3792, premium_collected=4349):
        """Initialize model with market parameters"""
        self.current_price = current_price
        self.monthly_capital = monthly_capital
        self.initial_portfolio = initial_portfolio
        self.premium_collected = premium_collected

        # Kelly Criterion parameters (from Monte Carlo optimization)
        self.kelly_fraction = 0.062  # 6.2% optimal edge
        self.personal_factor = 0.50  # 50% of Kelly for aggressive but prudent

        # Strike allocation optimization (based on current $2.40 price)
        self.strike_weights = {
            2.00: 0.25,  # 25% weight - 100% assignment prob
            2.50: 0.35,  # 35% weight - 95% assignment prob  
            3.00: 0.25,  # 25% weight - 60% assignment prob
            4.00: 0.10,  # 10% weight - 20% assignment prob
            5.00: 0.05   # 5% weight - 5% assignment prob
        }

        # Premium allocation parameters
        self.put_allocation = 0.70   # 70% to put expansion
        self.call_allocation = 0.30  # 30% to call hedges

        # Call hedge ladder (optimized for recovery scenarios)
        self.hedge_strikes = {
            5.00: 0.40,   # 40% near-term protection
            7.50: 0.35,   # 35% medium-term upside
            12.50: 0.25   # 25% explosive capture
        }

    def calculate_optimal_position_size(self, portfolio_value, edge=0.15, 
                                      variance=0.25):
        """
        Calculate optimal position size using Kelly Criterion

        Args:
            portfolio_value: Current portfolio value
            edge: Expected return advantage (15% default)
            variance: Return variance (25% default for high IV)

        Returns:
            Optimal position size in dollars
        """
        kelly_optimal = edge / variance
        adjusted_kelly = kelly_optimal * self.personal_factor
        position_size = portfolio_value * adjusted_kelly

        return {
            'kelly_fraction': kelly_optimal,
            'adjusted_kelly': adjusted_kelly,
            'position_size': position_size,
            'position_percent': adjusted_kelly * 100
        }

    def assignment_probability_model(self, strike, days_to_expiry=27):
        """
        Calculate assignment probability based on strike vs current price

        Args:
            strike: Put strike price
            days_to_expiry: Days until expiration (default 27)

        Returns:
            Assignment probability (0.0 to 1.0)
        """
        moneyness = strike / self.current_price
        time_decay_factor = max(0.1, days_to_expiry / 30)  # Time value effect

        if strike <= self.current_price:
            # ITM puts: High assignment probability
            base_prob = 0.85
            itm_boost = (self.current_price - strike) / self.current_price * 0.15
            assignment_prob = min(1.0, base_prob + itm_boost)
        else:
            # OTM puts: Lower but non-zero assignment probability
            base_prob = 0.05
            otm_factor = (self.current_price / strike) * 0.8 * time_decay_factor
            assignment_prob = max(0.05, base_prob + otm_factor)

        return assignment_prob

    def effective_cost_calculator(self, strike, premium_collected):
        """
        Calculate effective cost basis after premium offset

        Args:
            strike: Put strike price
            premium_collected: Premium received per share

        Returns:
            Dictionary with cost basis analysis
        """
        effective_cost = strike - premium_collected
        profit_at_current = self.current_price - effective_cost
        profit_percent = (profit_at_current / effective_cost) * 100 if effective_cost > 0 else 0

        return {
            'strike': strike,
            'premium_collected': premium_collected,
            'effective_cost_basis': effective_cost,
            'profit_at_current_price': profit_at_current,
            'profit_percent': profit_percent,
            'discount_to_current': (1 - effective_cost/self.current_price) * 100
        }

    def monthly_compounding_cycle(self, current_premium, month_number=1):
        """
        Execute monthly premium compounding allocation

        Args:
            current_premium: Premium collected this month
            month_number: Current month (for scaling calculations)

        Returns:
            Allocation breakdown for puts and calls
        """
        # Progressive scaling factor (accounts for compounding growth)
        scaling_factor = 1 + (month_number - 1) * 0.15  # 15% monthly scaling

        # Allocation calculations
        put_reinvestment = current_premium * self.put_allocation
        call_hedge_budget = current_premium * self.call_allocation
        total_put_capital = put_reinvestment + self.monthly_capital

        # Contract estimation (based on weighted average strike)
        weighted_avg_strike = sum(strike * weight for strike, weight in self.strike_weights.items())
        contract_cost_estimate = weighted_avg_strike * 100  # Per contract cost
        estimated_new_contracts = int(total_put_capital / contract_cost_estimate)

        # Compounding metrics
        compounding_multiple = total_put_capital / self.monthly_capital
        monthly_growth_rate = (compounding_multiple - 1) * 100

        return {
            'month': month_number,
            'premium_collected': current_premium,
            'put_reinvestment': put_reinvestment,
            'call_hedge_budget': call_hedge_budget,
            'total_put_capital': total_put_capital,
            'monthly_capital_added': self.monthly_capital,
            'estimated_new_contracts': estimated_new_contracts,
            'weighted_avg_strike': weighted_avg_strike,
            'compounding_multiple': compounding_multiple,
            'monthly_growth_rate': monthly_growth_rate,
            'scaling_factor': scaling_factor
        }

    def assignment_management_protocol(self, assigned_shares, effective_cost_basis):
        """
        Define systematic assignment management strategy

        Args:
            assigned_shares: Number of shares assigned
            effective_cost_basis: Average cost per share

        Returns:
            Assignment management plan
        """
        total_share_value = assigned_shares * self.current_price
        total_cost_basis = assigned_shares * effective_cost_basis
        unrealized_profit = total_share_value - total_cost_basis

        # Covered call strategy (optional income enhancement)
        cc_strike = effective_cost_basis * 1.25  # 25% above cost basis
        cc_premium_estimate = max(0.10, (cc_strike - self.current_price) * 0.3)
        monthly_cc_income = assigned_shares * cc_premium_estimate

        return {
            'assigned_shares': assigned_shares,
            'effective_cost_basis': effective_cost_basis,
            'total_investment': total_cost_basis,
            'current_market_value': total_share_value,
            'unrealized_profit': unrealized_profit,
            'profit_percent': (unrealized_profit / total_cost_basis) * 100,
            'hold_strategy': 'INDEFINITE',  # Long-term conviction
            'covered_call_strike': cc_strike,
            'estimated_cc_premium': cc_premium_estimate,
            'monthly_cc_income': monthly_cc_income,
            'total_monthly_yield': (monthly_cc_income / total_share_value) * 100
        }

    def call_hedge_optimization(self, hedge_budget, recovery_scenarios=None):
        """
        Optimize call hedge allocation across strike ladder

        Args:
            hedge_budget: Total budget for call hedges
            recovery_scenarios: List of target recovery prices

        Returns:
            Optimized hedge allocation
        """
        if recovery_scenarios is None:
            recovery_scenarios = [5.0, 7.5, 12.5, 20.0]

        hedge_plan = []

        for strike, weight in self.hedge_strikes.items():
            allocation = hedge_budget * weight

            # Estimate contracts based on current option pricing
            if strike <= 5.0:
                estimated_premium = 0.35  # Near-term protection
            elif strike <= 10.0:
                estimated_premium = 0.25  # Medium-term upside
            else:
                estimated_premium = 0.15  # Long-term explosive

            contracts = int(allocation / (estimated_premium * 100))

            # Calculate breakeven and profit targets
            breakeven = strike + estimated_premium
            profit_scenarios = []

            for recovery_price in recovery_scenarios:
                if recovery_price > breakeven:
                    profit_per_contract = (recovery_price - strike) * 100 - (estimated_premium * 100)
                    total_profit = profit_per_contract * contracts
                    leverage_multiple = profit_per_contract / (estimated_premium * 100)
                    profit_scenarios.append({
                        'recovery_price': recovery_price,
                        'profit_per_contract': profit_per_contract,
                        'total_profit': total_profit,
                        'leverage_multiple': leverage_multiple
                    })

            hedge_plan.append({
                'strike': strike,
                'allocation_weight': weight,
                'budget_allocation': allocation,
                'estimated_premium': estimated_premium,
                'contracts': contracts,
                'breakeven_price': breakeven,
                'profit_scenarios': profit_scenarios
            })

        return hedge_plan

    def generate_6month_projections(self):
        """
        Generate comprehensive 6-month accumulation projections

        Returns:
            DataFrame with month-by-month projections
        """
        months_data = []
        cumulative_shares = 0
        cumulative_premium = self.premium_collected
        current_contracts = 38  # Starting contracts
        current_portfolio_value = self.initial_portfolio + self.premium_collected

        for month in range(1, 7):
            # Progressive return scaling (compounding effect)
            base_return = 0.08 + (month - 1) * 0.01  # 8% to 13% progression
            monthly_premium = current_portfolio_value * base_return

            # Compounding cycle calculation
            cycle = self.monthly_compounding_cycle(monthly_premium, month)
            cumulative_premium += monthly_premium

            # Position scaling
            new_contracts = cycle['estimated_new_contracts']
            current_contracts += new_contracts

            # Assignment calculations
            assignment_rate = min(0.80, 0.50 + month * 0.05)  # Progressive 50% to 80%
            monthly_assignments = int(new_contracts * assignment_rate)
            new_shares = monthly_assignments * 100
            cumulative_shares += new_shares

            # Cost basis and valuation
            effective_cost = cycle['weighted_avg_strike'] - (cycle['weighted_avg_strike'] * 0.45)
            share_value_current = cumulative_shares * self.current_price
            total_cost_basis = cumulative_shares * effective_cost

            # Portfolio value calculation
            current_portfolio_value += self.monthly_capital + (monthly_premium * 0.30)
            call_hedge_value = cycle['call_hedge_budget'] * month  # Cumulative
            total_portfolio_value = current_portfolio_value + share_value_current - total_cost_basis + call_hedge_value

            months_data.append({
                'Month': month,
                'Monthly_Premium': monthly_premium,
                'Put_Reinvestment': cycle['put_reinvestment'],
                'Call_Hedge_Budget': cycle['call_hedge_budget'],
                'New_Contracts': new_contracts,
                'Total_Contracts': current_contracts,
                'Monthly_Assignments': monthly_assignments,
                'New_Shares': new_shares,
                'Cumulative_Shares': cumulative_shares,
                'Effective_Cost_Per_Share': effective_cost,
                'Share_Value_Current': share_value_current,
                'Total_Cost_Basis': total_cost_basis,
                'Call_Hedge_Value': call_hedge_value,
                'Cumulative_Premium': cumulative_premium,
                'Portfolio_Value': total_portfolio_value,
                'Compounding_Multiple': cycle['compounding_multiple']
            })

        return pd.DataFrame(months_data)

    def appreciation_scenarios(self, final_shares, effective_cost, total_premium, 
                             hedge_value, target_prices=None):
        """
        Calculate long-term appreciation scenarios

        Args:
            final_shares: Total accumulated shares
            effective_cost: Average cost per share
            total_premium: Total premium collected
            hedge_value: Call hedge portfolio value
            target_prices: List of recovery target prices

        Returns:
            List of scenario dictionaries
        """
        if target_prices is None:
            target_prices = [5.0, 8.0, 12.0, 20.0, 30.0]

        scenarios = []
        scenario_names = ['Conservative', 'Moderate', 'Strong', 'Explosive', 'Extreme']

        for i, target_price in enumerate(target_prices):
            share_value = final_shares * target_price
            share_cost = final_shares * effective_cost
            share_profit = share_value - share_cost

            # Hedge profit estimation (conservative)
            price_multiple = target_price / self.current_price
            hedge_multiplier = min(15, price_multiple * 2)  # Cap at 15x
            hedge_profit = hedge_value * hedge_multiplier

            total_return = share_profit + total_premium + hedge_profit

            scenarios.append({
                'Scenario': scenario_names[i],
                'Target_Price': target_price,
                'Share_Value': share_value,
                'Share_Profit': share_profit,
                'Hedge_Profit': hedge_profit,
                'Total_Premium': total_premium,
                'Total_Return': total_return,
                'Price_Multiple': price_multiple,
                'Hedge_Leverage': hedge_multiplier
            })

        return scenarios

    def risk_metrics_calculator(self, portfolio_value, position_size, 
                               iv_level=425, time_horizon=30):
        """
        Calculate comprehensive risk metrics

        Args:
            portfolio_value: Current portfolio value
            position_size: Total position size
            iv_level: Implied volatility level (%)
            time_horizon: Risk time horizon in days

        Returns:
            Risk metrics dictionary
        """
        # Position concentration
        concentration = (position_size / portfolio_value) * 100

        # Value at Risk calculation (simplified)
        daily_vol = (iv_level / 100) / np.sqrt(252)  # Daily volatility
        var_95 = portfolio_value * daily_vol * 1.645  # 95% VaR
        var_99 = portfolio_value * daily_vol * 2.33   # 99% VaR

        # Maximum drawdown estimation
        max_drawdown_est = portfolio_value * (iv_level / 100) * 0.5

        # Assignment risk analysis
        assignment_risk_score = min(10, concentration / 10)  # Scale 1-10

        return {
            'portfolio_value': portfolio_value,
            'position_size': position_size,
            'concentration_percent': concentration,
            'daily_var_95': var_95,
            'daily_var_99': var_99,
            'max_drawdown_estimate': max_drawdown_est,
            'iv_level': iv_level,
            'assignment_risk_score': assignment_risk_score,
            'risk_rating': 'AGGRESSIVE' if concentration > 80 else 'MODERATE'
        }

# Usage Example and Testing
if __name__ == "__main__":
    # Initialize model with current market conditions
    model = ASSTPremiumCompounder(
        current_price=2.40,
        monthly_capital=4000,
        initial_portfolio=3792,
        premium_collected=4349
    )

    print("ASST Volatility Arbitrage Model Initialized")
    print("Current Price: $2.40")
    print("Monthly Capital: $4,000")
    print("Strategy: Aggressive Share Accumulation")

    # Generate 6-month projections
    projections = model.generate_6month_projections()
    print("\n6-Month Projections Generated:")
    print(projections[['Month', 'Cumulative_Shares', 'Portfolio_Value']].to_string(index=False))

    # Calculate final scenarios
    final_data = projections.iloc[-1]
    scenarios = model.appreciation_scenarios(
        final_data['Cumulative_Shares'],
        final_data['Effective_Cost_Per_Share'],
        final_data['Cumulative_Premium'],
        final_data['Call_Hedge_Value']
    )

    print("\nAppreciation Scenarios:")
    for scenario in scenarios:
        print(f"{scenario['Scenario']}: ${scenario['Target_Price']:.2f} = ${scenario['Total_Return']:,.0f}")

    print("\nModel Ready for Live Implementation")
