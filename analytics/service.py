"""Deterministic portfolio analytics tool, exposed over HTTP for Make.

This is the "Python = deterministic computation" layer of the architecture:
the LLM never does this arithmetic itself, it only calls /analytics and
narrates the numbers it gets back.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI

from portfolio import PORTFOLIO
from retrieval import retrieve
from var_models import historical_var, portfolio_returns

app = FastAPI(title="Portfolio Analytics Tool")

DATA_PATH = Path(__file__).parent.parent / "data" / "mock_prices.csv"
VOL_WINDOW_DAYS = 20
VAR_CONFIDENCE = 0.99


def load_prices() -> pd.DataFrame:
    """Load the mock daily close prices, one column per ticker."""
    return pd.read_csv(DATA_PATH, index_col="date", parse_dates=True)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/analytics")
def get_analytics() -> dict:
    """Compute the portfolio risk snapshot: returns, vol, VaR, concentration,
    top contributors/detractors, the numbers a risk analyst would check
    before answering "has anything breached a limit today?"
    """
    prices = load_prices()
    returns = prices.pct_change().dropna()
    weights = PORTFOLIO.weights
    port_rets = portfolio_returns(returns, weights)

    last_return = port_rets.iloc[-1]
    vol_recent = port_rets.tail(VOL_WINDOW_DAYS).std() * np.sqrt(252)
    var_99 = historical_var(port_rets, confidence_level=VAR_CONFIDENCE, notional=PORTFOLIO.notional)

    nav_curve = (1 + port_rets).cumprod()
    drawdown_from_peak = (nav_curve / nav_curve.cummax() - 1).iloc[-1]

    last_day_contrib = returns.iloc[-1].mul(weights).sort_values(ascending=False)

    # All percentage-like fields below are scaled to percentage POINTS
    # (e.g. 2.11, not 0.0211) so a literal "%" can always be appended
    # after them without any caller having to guess or convert units.
    return {
        "as_of": str(prices.index[-1].date()),
        "notional": PORTFOLIO.notional,
        "portfolio_return_1d_pct": round(float(last_return) * 100, 2),
        "vol_20d_annualized_pct": round(float(vol_recent) * 100, 2),
        "historical_var_99_1d": {
            "amount": round(float(var_99), 2),
            "pct_of_nav_pct": round(float(var_99 / PORTFOLIO.notional) * 100, 2),
        },
        "drawdown_from_peak_pct": round(float(drawdown_from_peak) * 100, 2),
        "largest_position_pct": round(float(weights.max()) * 100, 2),
        "individual_returns_1d_pct": (returns.iloc[-1] * 100).round(2).to_dict(),
        "top_contributors_1d_pct": (last_day_contrib.head(3) * 100).round(2).to_dict(),
        "top_detractors_1d_pct": (last_day_contrib.tail(3) * 100).round(2).to_dict(),
    }


@app.get("/policy")
def get_policy(query: str, top_k: int = 2) -> dict:
    """Retrieve the policy sections most relevant to a natural-language query.

    e.g. /policy?query=has the portfolio breached any risk limits
    """
    return {"query": query, "results": retrieve(query, top_k=top_k)}
