"""Generate synthetic daily close prices for the 16-stock NSE universe.

Stands in for live market data so the agent prototype has no external data
dependency (no Kite auth, no rate limits). The only contract downstream code
relies on is the CSV shape: a date index, one column per ticker. Swap this
for real historical data later without touching the analytics tool.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

TICKERS: tuple[str, ...] = (
    "HDFCBANK", "ICICIBANK", "SBIN", "TCS", "INFY", "WIPRO",
    "RELIANCE", "ONGC", "HINDUNILVR", "ITC", "MARUTI", "M&M",
    "SUNPHARMA", "DRREDDY", "TATASTEEL", "ULTRACEMCO",
)

# Rough Sep-2026 ballpark starting prices and annualized vol per ticker,
# just enough spread that per-stock risk output looks plausible, not a
# claim of accuracy.
START_PRICES: dict[str, float] = {
    "HDFCBANK": 1650.0, "ICICIBANK": 1250.0, "SBIN": 820.0, "TCS": 4100.0,
    "INFY": 1850.0, "WIPRO": 560.0, "RELIANCE": 2950.0, "ONGC": 260.0,
    "HINDUNILVR": 2450.0, "ITC": 470.0, "MARUTI": 12500.0, "M&M": 2850.0,
    "SUNPHARMA": 1780.0, "DRREDDY": 6700.0, "TATASTEEL": 165.0, "ULTRACEMCO": 11200.0,
}
ANNUAL_VOL: dict[str, float] = {
    "HDFCBANK": 0.20, "ICICIBANK": 0.24, "SBIN": 0.30, "TCS": 0.22,
    "INFY": 0.25, "WIPRO": 0.28, "RELIANCE": 0.24, "ONGC": 0.32,
    "HINDUNILVR": 0.18, "ITC": 0.19, "MARUTI": 0.26, "M&M": 0.29,
    "SUNPHARMA": 0.27, "DRREDDY": 0.26, "TATASTEEL": 0.34, "ULTRACEMCO": 0.23,
}

TRADING_DAYS = 260  # roughly one year of business days
SEED = 42  # fixed so the "market" is reproducible across runs


def generate_prices() -> pd.DataFrame:
    """Simulate one correlated GBM-style price path per ticker.

    Each ticker's daily return is a blend of a shared market shock and
    idiosyncratic noise, scaled to that ticker's annual vol. This gives
    realistic-looking cross-stock correlation (so portfolio vol is lower
    than the average single-stock vol) without hand-building a full
    covariance matrix.
    """
    rng = np.random.default_rng(SEED)
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=TRADING_DAYS)

    market_shock = rng.normal(0, 1, size=TRADING_DAYS)
    daily_returns = pd.DataFrame(index=dates, columns=TICKERS, dtype=float)

    for ticker in TICKERS:
        sigma_daily = ANNUAL_VOL[ticker] / np.sqrt(252)
        idio = rng.normal(0, 1, size=TRADING_DAYS)
        market_loading = rng.uniform(0.5, 0.9)
        shock = market_loading * market_shock + np.sqrt(1 - market_loading**2) * idio
        drift = -0.5 * sigma_daily**2  # zero expected log-return
        daily_returns[ticker] = drift + sigma_daily * shock

    log_prices = np.log(pd.Series(START_PRICES)) + daily_returns.cumsum()
    prices = np.exp(log_prices)
    prices.index.name = "date"
    return prices.round(2)


if __name__ == "__main__":
    prices = generate_prices()
    out_path = Path(__file__).parent / "mock_prices.csv"
    prices.to_csv(out_path)
    #prices.to_csv("mock_prices.csv")
    print(f"Wrote {len(prices)} rows x {len(TICKERS)} tickers to {out_path}")
