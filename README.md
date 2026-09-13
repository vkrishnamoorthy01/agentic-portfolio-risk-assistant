# Agentic Portfolio Risk Assistant

A small prototype built to understand the practical difference between a
deterministic workflow, an LLM with tool-calling, a genuinely agentic
system, RAG, and MCP. Built around a Portfolio Risk Analyst agent for a
16-stock NSE equity portfolio.

Not a production system. Scope, tools, and infra are deliberately minimal.

## Portfolio

Equal-weighted, ₹1 crore notional: HDFCBANK, ICICIBANK, SBIN, TCS, INFY,
WIPRO, RELIANCE, ONGC, HINDUNILVR, ITC, MARUTI, M&M, SUNPHARMA, DRREDDY,
TATASTEEL, ULTRACEMCO. Same universe as the `risk_project` in
`quant_risk_and_trading_portfolio`; the VaR/analytics logic here is ported
from that project rather than rebuilt.

## Architecture

```
User -> Make.com (orchestrator) -> Portfolio Analytics tool (Python, deterministic)
                                 -> Risk Policy RAG (embeddings over a short policy doc)
     -> synthesized risk assessment -> human approval for any consequential action
```

- **Market data**: synthetic daily prices for the 16 tickers, `data/generate_mock_data.py`
  (no live Kite dependency - swappable later).
- **Analytics tool**: Python service (ported from `risk_project`), exposing
  deterministic calculations (returns, vol, contributors, concentration,
  historical VaR) over HTTP. The LLM never does the arithmetic itself.
- **RAG**: a short fictional risk policy document, retrieved via real
  embedding + cosine-similarity search (no vector DB needed at this scale).
- **Orchestrator**: Make.com (free plan). V1 uses a plain fixed scenario;
  V4 swaps in Make's AI Agent module so the LLM decides which tools to call.
- **Local hosting**: the Python service runs locally, tunneled to Make via
  ngrok (free) so Make's HTTP modules can reach it.
- **MCP (V5)**: `analytics/mcp_server.py` wraps the same `get_analytics`/
  `retrieve` logic as MCP tools (stdio transport), registered via
  `.mcp.json` at the project root. Host/client used: Claude Code itself,
  no ngrok, no cloud infra, since MCP over stdio talks to a local process
  directly.

## Running it

Needs Python 3.11+ and pip. Install deps:

```
pip install -r requirements.txt
```

No API keys or environment variables needed to run anything in this repo.
The mock price data (`data/mock_prices.csv`) is already generated and
checked in; regenerate it with `python data/generate_mock_data.py` if you
want (fixed seed, so output is the same either way).

**MCP path (V5, easiest to try locally):** point an MCP host (Claude Code
is what this was built and tested against) at this project directory.
`.mcp.json` registers `analytics/mcp_server.py` as a stdio server; the
host starts it and discovers `get_portfolio_analytics` and
`get_risk_policy_sections` on its own.

**HTTP path (V1-V4):**

```
cd analytics
uvicorn service:app --reload
```

Then hit `http://localhost:8000/analytics` or
`http://localhost:8000/policy?query=...` directly. Wiring this into Make.com
the way V1-V4 do also needs an ngrok tunnel (Make is cloud-hosted and can't
reach localhost) and a Make scenario with an Anthropic API key configured
in Make's UI. Both of those live outside this repo entirely, so they're
not something you can reproduce just by cloning it. The code here only
covers the local Python side.

## Status

- [x] V1 step 1: project scaffold + synthetic 16-stock daily price data (`data/mock_prices.csv`, 260 trading days)
- [x] V1: bare Make scenario, one fixed LLM call (Webhooks > Custom webhook -> Anthropic Claude "Simple Text Prompt" -> Webhooks > Webhook response). Working end-to-end.
- [x] V2: `analytics/service.py` FastAPI app ported from `risk_project`, exposing `GET /analytics` (portfolio return, 20-day vol, 99% historical VaR, drawdown, concentration, top contributors/detractors, individual returns, all percentage fields pre-scaled to percentage points with `_pct` suffixes so no caller has to guess units), tunneled via ngrok, wired into the Make scenario (HTTP > Make a request module between Webhooks and Anthropic Claude). Working end-to-end, verified against live output.
- [x] V3: `policy/risk_policy.md` drafted and `analytics/retrieval.py` built: chunking (split on `## ` headers) + local embeddings (`sentence-transformers`, `all-MiniLM-L6-v2`) + in-memory cosine-similarity search, exposed as `GET /policy?query=...`. Wired into the Make scenario as a second HTTP module; Claude now explicitly states breach/no-breach per policy section (verified live: correctly flagged volatility as RED-breach and VaR as compliant, citing the right sections). Working end-to-end.
- [x] V4: separate Make scenario `Agentic_portfolio_risk_assistant_v4` (cloned and cleaned from the original mixed-up scenario; `Agentic_portfolio_risk_assistant_v3` holds the V1-V3 deterministic baseline). Webhooks (Custom webhook) -> Make AI Agent (model: Anthropic Claude Haiku 4.5; two tools: `get_portfolio_analytics` -> `GET /analytics`, `get_risk_policy_sections` -> `GET /policy?query=<agent-decided>&top_k=2`) -> Webhooks (Webhook response, mapped to the Agent's `Response` field). Verified end-to-end with three tool-selective questions, see the comparison table and full build notes below.
- [x] V5: `analytics/mcp_server.py`, same `get_analytics`/`retrieve` logic exposed as two MCP tools (`get_portfolio_analytics`, `get_risk_policy_sections`) over stdio, registered via `.mcp.json`, consumed by Claude Code as the MCP host/client. Verified: tool discovery happened automatically (no hand-typed tool description, unlike Make's Agent in V4) and tool invocation worked live in-conversation, see the V5 section below.
- [ ] Guardrails / AML-analogy discussion

## V4 results: agentic tool selection vs. V1-V3's fixed sequence

Verified via Make's execution-log "Execution steps" trace, not just inferred
from the answer text; each row below is confirmed by watching the actual
tool-call sequence in History, not assumed:

| Question | Tools called | Agent credits | What it shows |
|---|---|---|---|
| "What is my largest position?" | `get_portfolio_analytics` only | 6.26 | recognized it needed live numbers, not policy |
| "What does VaR mean?" | none | 4.46 | recognized a pure knowledge question, called nothing |
| "Are there any serious risk issues in my portfolio today?" | `get_portfolio_analytics` -> `get_risk_policy_sections` (sequential) | 8.87 | got numbers first, then checked them against policy limits before answering |

For the third question, the agent correctly classified 20-day volatility as a
RED-zone policy breach (22.88% vs. the 20% threshold) while confirming
concentration and VaR were within limits, a genuine breach determination,
not a templated answer, since the fixed V1-V3 pipeline never had to make
that judgment call itself (the prompt already told it what to check).

This is the concrete contrast with `_v3`: `_v3` always calls both HTTP
tools in the same fixed order regardless of the question (live data, but a
deterministic *workflow*); `_v4`'s tool-call count and sequence visibly
change based on what the question actually needs: 0, 1, or 2 tool calls,
decided by the model itself. Credit cost scales with that flexibility
(4.46 -> 6.26 -> 8.87 credits as more tool calls were needed), a concrete
number to cite when discussing agentic-vs-deterministic cost tradeoffs.

## V5 results: MCP vs. direct HTTP wiring

`analytics/mcp_server.py` exposes the exact same two capabilities as V1-V4's
HTTP endpoints, just over MCP instead of raw HTTP: same underlying
functions (`get_analytics`, `retrieve`), imported directly rather than
duplicated. Registered via a three-line `.mcp.json` at the project root.

**Host/client/server mapping for this exercise:** Claude Code is both the
MCP host (the application) and client (the protocol implementation inside
it) in this setup; `mcp_server.py` running as a local subprocess over
stdio is the MCP server. No network, no ngrok, no cloud infra needed,
unlike every prior stage, which required tunneling a local service to be
reachable from Make's cloud.

**What MCP added over Make's direct HTTP wiring (V1-V4), concretely
observed, not just asserted:**
- **Discovery**: changing this session's working directory to the project
  folder was enough for Claude Code to find and load the two tools
  automatically from the server's decorators/docstrings: no hand-typed
  tool name, description, or URL anywhere. Compare to V4, where every tool
  needed a manually written name + description + URL inside Make's UI
  before the Agent could use it, and the description text had to stay in
  sync with what the endpoint actually did by hand.
- **Invocation**: asked a real question, "Am I overweighted on any
  sector? Does it breach policy limits? Should I be concerned about
  concentration risk?", and Claude Code called both
  `get_portfolio_analytics` and `get_risk_policy_sections` on its own,
  same class of tool-selection decision as V4's Make Agent, just over a
  different transport.

**A genuine finding from that test, not staged:** neither tool actually
supports sector-level analysis: the analytics tool only returns per-stock
weights, and the policy document only defines a per-*position* limit, no
sector rule at all. The correct answer required admitting that gap rather
than inventing a sector limit that doesn't exist, while still being useful
(computing sector totals as plain arithmetic on the equal weights already
returned, clearly labeled as not tool-verified data). A concrete example
of avoiding hallucination when a question exceeds what the available tools
actually cover, a real instance of exactly the kind of guardrail failure
this project set out to explore, caught in the course of normal use rather
than deliberately engineered as a test case.

## Notable bugs & lessons

**Percentage/unit-conversion bug (V2, 2026-09-12).** `analytics/service.py`
originally returned percentage-like fields as raw fractions (e.g. `0.0211`
for 2.11%). The Make scenario's Claude prompt had literal `% of NAV` text
hardcoded right after the VaR fraction, so it rendered as **"0.0211% of
NAV"** instead of "2.11% of NAV", a real, live-tested output, not a
hypothetical. Three *other* fields in the same prompt (return, vol,
drawdown) had no `%` hardcoded next to them, and Claude happened to
correctly infer a ×100 conversion when writing its prose for those, so the
prompt was right 3 times out of 4, by luck, not by design.

This is a small but genuine illustration of the project's core principle,
"the LLM should not perform important numerical calculations itself",
extending further than it first appears. It's not just about VaR/vol/return
arithmetic; unit conversion and formatting are numerical operations too,
and this pipeline was silently relying on the model to get them right.

**Fix:** moved the conversion into `service.py` itself. Every
percentage-like field is now pre-scaled to percentage points and renamed
with an explicit `_pct` suffix (`portfolio_return_1d_pct`,
`vol_20d_annualized_pct`, `historical_var_99_1d.pct_of_nav_pct`,
`drawdown_from_peak_pct`, `largest_position_pct`), so appending a literal
`%` in the prompt is always correct, no inference required anywhere in
the chain. Required re-mapping the Claude prompt's field chips once, since
Make doesn't auto-migrate mappings when an upstream field is renamed.

**Retrieval-quality finding (V3, 2026-09-12).** With only 5 short policy
chunks that initially shared a lot of generic boilerplate ("must be
reviewed by a risk officer", "escalated", "breach" in nearly every
section), the small local embedding model (`all-MiniLM-L6-v2`) struggled
to tell them apart. Concretely: the query *"is the portfolio too
volatile"*, using the literal word "volatile", ranked the actual
Volatility Thresholds section **3rd out of 5**, behind Drawdown Escalation
and Position Concentration.

**Fix (partial):** rewrote the policy doc so each section's escalation
instructions live only in Section 5, leaving Sections 1-4 to use more
topically distinct vocabulary (concentration/diversification vs.
volatility/turbulence vs. tail-risk/VaR vs. drawdown/underwater). That
alone fixed the direct case: "is the portfolio too volatile" now
correctly ranks Volatility Thresholds 1st.

**What didn't get fixed, deliberately left as a real finding:** the
colloquial query *"is the fund too jumpy right now"* still ranks
Volatility Thresholds **last**, even after the chunking rewrite. That's
not a chunking problem, it's the actual ceiling of a small, free, local
embedding model on slang/colloquial phrasing. Kept as-is rather than
swapping to a larger model or adding query rewriting, since it's a
genuine, reproducible "incorrect retrieval" case study, exactly the kind
of guardrails/HITL failure mode this project cares about, that's more
useful to speak to concretely than to paper over.

**Make array-mapping quirk (V3, 2026-09-12).** Make's field-picker only
offers a flattened preview for a repeating/array field (like `/policy`'s
`results` array) rather than separate per-index entries, clicking it
doesn't cleanly grab "just item 1". Fix: type the reference directly
instead of clicking, using Make's 1-based bracket syntax:
`{{8.data.results[1].text}}` / `{{8.data.results[2].text}}` (module
number, then `.data.<arrayField>[N].<subfield>`). Worth remembering for
V4, where tool outputs will likely hit the same pattern.

**Make's "agentic scenario" wizard silently sets a Schedule trigger, not a webhook (V4, 2026-09-13).** Building `_v4` via Make's "Create agentic scenario" wizard (as opposed to a plain blank scenario) produced a scenario whose real registered trigger was a leftover Schedule module ("run every 15 minutes"), even after a Custom Webhook module was added and visually sat first in the chain. Symptoms: webhook test calls failed with "There is no scenario listening for this webhook" regardless of timing; execution History showed spurious "Success, 0 operations" entries (the scenario firing on its own 15-minute schedule with no real data); the scenario-list view's trigger-type icon showed a clock instead of a lightning bolt, that list-level icon turned out to be the fastest way to confirm the diagnosis. The Custom Webhook module itself was also visibly missing the lightning-bolt "this is the trigger" overlay that a properly-triggering webhook shows. Deleting the stray Schedule module via the canvas UI proved awkward (right-click did nothing); the practical fix was abandoning that scenario and rebuilding from a plain blank scenario instead, which produces a correctly-triggering webhook by default. **Lesson: for a Make scenario that needs a genuine instant-webhook trigger, start from a plain blank scenario, not a template/wizard flow. Templates may bake in a different trigger model than they visually suggest.**

**A costly transcription typo, not a Make bug (V4, 2026-09-13).** After the above was fixed, one specific test question kept failing with a genuine HTTP 404 ("Not found") while others succeeded, which led to an extended (wrong) investigation into webhook-arming race conditions and "first request after Run once always fails" theories. The actual cause: the assistant helping debug this (Claude) mistyped the webhook URL in one message, dropping one character from the token (`...rmroovjv74` vs. the correct `...rmrooovjv74`), and the user was correctly copy-pasting that typo for every subsequent new test while an old, correctly-typed command lingered in shell history and kept "coincidentally" working. **Lesson: when a webhook fails intermittently in a way that doesn't fit the mechanism being suspected, diff the literal URL string character-by-character before investigating timing/infrastructure theories.**

**Make's per-tool parameter UI: static value vs. agent-decided (V4, 2026-09-13).** In a Make AI Agent's tool configuration, a query parameter with a filled-in Value is always sent as that literal value; leaving Value blank (with only a Name defined) appears to let the agent supply that argument itself at call time. There is a separate section-level "Let AI Agent decide" checkbox, but it hands the *entire* parameter set (names and values) to the model's judgment rather than letting you fix some parameters while leaving others open. Used the per-parameter blank-value approach instead: `top_k` fixed at `2`, `query` left blank so the agent could in principle supply it (in practice it just passes the user's raw question through, which is an acceptable simplification, reformulating the search query is a nice-to-have, not the core lesson of V4).

**MCP Python SDK breaking rename (V5, 2026-09-13).** `pip install mcp` installed 2.x, whose top-level API renamed `FastMCP` (the class most tutorials/examples reference) to `MCPServer` under `mcp.server.mcpserver`. `from mcp.server.fastmcp import FastMCP` fails outright on this version with a `ModuleNotFoundError` that (helpfully) names the new import path directly in its error message. `MCPServer` otherwise mirrors `FastMCP`'s interface (`.tool()` decorator, `.run()`), so the fix was a two-line import change, not a rewrite. Worth knowing before following any MCP Python tutorial dated before this rename.
