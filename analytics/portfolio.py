"""Portfolio configuration for the agentic risk assistant.

Ported from risk_project/portfolio.py in quant_risk_and_trading_portfolio,
same 16-stock universe, same equal-weighted notional.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PortfolioConfig:
    """Equal-weighted NSE equity portfolio definition."""

    tickers: tuple[str, ...]
    notional: float

    @property
    def weights(self) -> pd.Series:
        """Equal weight per ticker, summing to 1.0."""
        weight = 1.0 / len(self.tickers)
        return pd.Series(weight, index=list(self.tickers), name="weight")


PORTFOLIO = PortfolioConfig(
    tickers=(
        "HDFCBANK", "ICICIBANK", "SBIN", "TCS", "INFY", "WIPRO",
        "RELIANCE", "ONGC", "HINDUNILVR", "ITC", "MARUTI", "M&M",
        "SUNPHARMA", "DRREDDY", "TATASTEEL", "ULTRACEMCO",
    ),
    notional=10_000_000.0,
)
