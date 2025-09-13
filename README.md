# Pegger — a vibe-coded stablecoin analytics toy

This is a tiny, vibe-coded dashboard that shows three things in one place:

- Peg Monitor — live prices for **USDC / USDT / DAI** (via DefiLlama)
- Liquidity Sim — constant-product slippage for **1m / 5m / 10m** trades
- Yield Curve — simple USDC term curve from live lending anchors (Aave/Compound via DefiLlama)

Minimal stack: FastAPI + a sprinkling of Plotly.js. No DB. All in-memory. Live-only data.

## Quickstart (zero fuss)

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

### Launch the web dashboard

```bash
python main.py web --host 127.0.0.1 --port 8001
```
Open `http://127.0.0.1:8001`.

Tabs:
- Peg Monitor — live prices from DefiLlama (auto-refresh ~3s)
- Liquidity Sim — slippage curve + table (no fees, constant product)
- Yield Curve — interpolated from live Aave/Compound USDC APY

### CLI mode (just vibes in your terminal)

```bash
python main.py cli
```
Prints:
- Live peg snapshot table
- Slippage table for 50m/50m pool at 1m/5m/10m trade sizes
- Sample of the interpolated USDC yield curve

## REST Endpoints

- `GET /peg` — live stablecoin prices (DefiLlama). Returns 502 if unavailable.
- `GET /slippage?reserve_x=50000000&reserve_y=50000000&size=1000000` — constant product summary + optional query size
- `GET /yield` — live USDC anchors (Aave/Compound) + interpolated 1–30d curve. 502 on failure.

## Notes

- Live-only: no synthetic price fallback, no file-based yields. If upstream is down, you’ll see a 502.
- Slippage model is intentionally simple (no fees, constant product) — it’s a demo.
- The UI is intentionally minimal: fast to load, easy to demo.

## Vibe-coded commit ethos

- Keep it small, clear, and demo-friendly.
- Prioritize "does it show the concept?" over knobs.
- One script to rule them all (`main.py`).

---

Made for quick demos and good vibes. Not investment advice. ✌️
