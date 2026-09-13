# Portfolio Risk Policy

*Hypothetical policy document, written for this prototype. Not linked to any real firm.*

## 1. Position Concentration Limit

No single position may exceed 10% of portfolio NAV. This limit exists to
prevent idiosyncratic, single-name risk from dominating overall portfolio
risk, even a well-researched position can go wrong, and diversification
across names is the primary defense against that. A position between 8%
and 10% of NAV is a soft warning zone, not yet a breach.

## 2. Volatility Thresholds

Portfolio risk is classified using 20-day annualized volatility, a measure
of how sharply daily prices are swinging up and down:

- **Green**: below 15%, calm, typical market conditions.
- **Amber**: 15% to 20%, choppy, turbulent trading.
- **Red**: above 20%, highly volatile, large daily price swings.

## 3. Value-at-Risk Limit

The 99% one-day historical Value-at-Risk (VaR) estimates the worst
single-day loss expected under normal market conditions, a tail-risk
measure, not a typical-day figure. This estimated worst-case loss must not
exceed 3% of portfolio NAV.

## 4. Drawdown Threshold

Drawdown measures the decline from the portfolio's peak NAV down to its
current value, how far underwater the portfolio is, not a single day's
move. A drawdown beyond 8% from peak signals a sustained losing streak
rather than one bad trading day.

## 5. Escalation Procedure

Any of the following triggers escalation to a human risk officer before
further trading: a Red volatility classification (Section 2), a VaR
breach (Section 3), a drawdown beyond the Section 4 threshold, or a
position beyond the Section 1 concentration limit. Every escalation must
be logged and reviewed by a person, no automated system or agent may
execute trades on the basis of this policy alone.
