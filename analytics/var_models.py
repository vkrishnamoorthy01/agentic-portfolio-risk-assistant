"""Historical Value-at-Risk and portfolio return aggregation.

Ported from risk_project/var_models.py in quant_risk_and_trading_portfolio.
"""

from __future__ import annotations

import pandas as pd


def portfolio_returns(returns: pd.DataFrame, weights: pd.Series) -> pd.Series:
    """Compute a weighted portfolio return series from individual asset returns.

    Args:
        returns: DataFrame of asset returns, one column per ticker.
        weights: Portfolio weights indexed by ticker, summing to 1.0.

    Returns:
        Series of portfolio returns aligned to `returns`' index.
    """
    aligned_weights = weights.reindex(returns.columns)
    return returns.mul(aligned_weights, axis=1).sum(axis=1)


def historical_var(returns: pd.Series, confidence_level: float, notional: float = 1.0) -> float:
    """Compute historical (empirical) VaR from a portfolio return series.

    Takes the empirical quantile of realized returns directly, so it makes no
    distributional assumption but is only as good as the historical sample.

    Args:
        returns: Portfolio return series.
        confidence_level: Confidence level, e.g. 0.95 or 0.99.
        notional: Portfolio notional value used to scale VaR into currency terms.

    Returns:
        VaR as a positive number representing potential loss.
    """
    quantile = 1.0 - confidence_level
    var_return = returns.quantile(quantile)
    return -notional * var_return
