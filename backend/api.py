from contextlib import asynccontextmanager
from typing import List, Dict, Tuple, Deque

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from lib.amm import compute_slippage_summary
from lib.yield_curve import build_usdc_yield_curve
from lib.defillama import fetch_current_prices, fetch_stablecoin_prices, fetch_usdc_lending_anchors
from lib.peg import PegDataStore, start_price_background_updater
import json
from pathlib import Path
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
import threading
import time
import math


SYMBOLS: List[str] = ["USDC", "USDT", "DAI"]
VENUES: List[str] = ["Binance", "Curve"]

# In-memory live store + short history for sparklines
STORE: PegDataStore = PegDataStore(SYMBOLS, VENUES)
HISTORY: Dict[Tuple[str, str], Deque[Dict[str, object]]] = defaultdict(lambda: deque(maxlen=120))  # ~6 minutes @ 3s


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Re-anchor synthetic prices to live DefiLlama on startup (best-effort)
    try:
        live = fetch_current_prices(SYMBOLS)
        # Small venue offsets so spreads exist (around ~10 bps total)
        venue_offset = {"Binance": -0.0005, "Curve": 0.0005}
        with STORE._lock:  # type: ignore[attr-defined]
            now_iso = datetime.now(timezone.utc).isoformat()
            for v in VENUES:
                for s in SYMBOLS:
                    base = live.get(s, {}).get("price", 1.0)
                    price = max(0.90, min(1.10, float(base) + venue_offset.get(v, 0.0)))
                    STORE._prices[(v, s)] = price  # type: ignore[attr-defined]
                    STORE._timestamps[(v, s)] = now_iso  # type: ignore[attr-defined]
    except Exception:
        pass

    # Start random walk updater
    start_price_background_updater(STORE, interval_seconds=3.0)

    # Start history sampler thread
    stop_flag = {"stop": False}

    def _sample_history_loop():
        while not stop_flag["stop"]:
            try:
                rows = STORE.snapshot()
                for r in rows:
                    key = (str(r["venue"]), str(r["symbol"]))
                    HISTORY[key].append({"t": r["timestamp"], "p": r["price"]})
            except Exception:
                pass
            time.sleep(3.0)

    t = threading.Thread(target=_sample_history_loop, daemon=True)
    t.start()

    try:
        yield
    finally:
        stop_flag["stop"] = True


app = FastAPI(title="Weal: Stablecoin Analytics (Prototype)", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# CORS for Next.js dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev-friendly: allow any origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/peg")
def get_peg_snapshot():
    try:
        rows = STORE.snapshot()
        return JSONResponse(content={"data": rows})
    except Exception:
        return JSONResponse(status_code=502, content={"error": "Failed to fetch prices"})


@app.get("/peg_history")
def get_peg_history(symbol: str | None = Query(default=None), limit: int = Query(default=120, ge=1, le=1000)):
    try:
        symbols = [symbol.upper()] if symbol else SYMBOLS
        out: Dict[str, Dict[str, List[Dict[str, object]]]] = {}
        for s in symbols:
            out[s] = {}
            for v in VENUES:
                key = (v, s)
                points = list(HISTORY.get(key, deque()))
                # take last N
                out[s][v] = points[-limit:]
        return JSONResponse(content={"data": out})
    except Exception:
        return JSONResponse(status_code=502, content={"error": "Failed to fetch history"})


@app.get("/replay/usdc_2023")
def replay_usdc_2023():
    try:
        # Synthetic March 2023 USDC depeg-style path (~60 points)
        now = datetime.now(timezone.utc)
        n = 60
        times = [(now - timedelta(seconds=3 * (n - 1 - i))).isoformat() for i in range(n)]
        # Build a curve: start 1.000 -> trough 0.885 -> partial recovery 0.97
        values = []
        for i in range(n):
            t = i / (n - 1)
            if t < 0.5:
                # drop
                v = 1.0 - 0.23 * (t / 0.5)  # to ~0.77 if linear, clip later
            else:
                # recover
                v = 0.885 + (0.97 - 0.885) * ((t - 0.5) / 0.5)
            v = max(0.88, min(1.02, v))
            values.append(v)
        binance = [ round(v + 0.003, 6) for v in values ]
        curve = [ round(v - 0.003, 6) for v in values ]
        pts_b = [{"t": times[i], "p": binance[i]} for i in range(n)]
        pts_c = [{"t": times[i], "p": curve[i]} for i in range(n)]
        return JSONResponse(content={"data": {"USDC": {"Binance": pts_b, "Curve": pts_c}}})
    except Exception:
        return JSONResponse(status_code=502, content={"error": "Failed to build replay"})


@app.get("/slippage")
def get_slippage(reserve_x: float = 50_000_000, reserve_y: float = 50_000_000, size: float = 0.0):
    sizes = [1_000_000.0, 5_000_000.0, 10_000_000.0]
    rows = compute_slippage_summary(reserve_x, reserve_y, sizes)
    extra = None
    if size > 0:
        extra = compute_slippage_summary(reserve_x, reserve_y, [size])[0]
    return JSONResponse(
        content={
            "reserves": {"x": reserve_x, "y": reserve_y},
            "sizes": sizes,
            "summary": rows,
            "query": extra,
        }
    )


@app.get("/slippage_grid")
def get_slippage_grid(
    reserve_x: float = 50_000_000,
    reserve_y: float = 50_000_000,
    depth_multipliers: str = Query(default="0.5,1.0,1.5,2.0"),
    max_size_millions: int = Query(default=20, ge=1, le=100),
):
    try:
        depths = [float(x) for x in depth_multipliers.split(",") if x.strip()]
        sizes = [float(i) * 1_000_000.0 for i in range(1, max_size_millions + 1)]
        z: List[List[float]] = []
        for d in depths:
            rows = compute_slippage_summary(reserve_x * d, reserve_y * d, sizes)
            z.append([r["slippage_bps"] for r in rows])
        return JSONResponse(content={
            "x_sizes_mm": [s / 1_000_000.0 for s in sizes],
            "y_depth_multipliers": depths,
            "z_slippage_bps": z,
        })
    except Exception:
        return JSONResponse(status_code=502, content={"error": "Failed to compute grid"})


@app.get("/yield")
def get_yield_curve():
    # Live-only anchors
    try:
        live = fetch_usdc_lending_anchors()
        if not live:
            return JSONResponse(status_code=502, content={"error": "Live yields unavailable"})
        payload = build_usdc_yield_curve(live)
        # Compute simple CeFi vs DeFi delta (bps)
        cefi_keys = [k for k in live.keys() if "binance" in k.lower()]
        defi_keys = [k for k in live.keys() if k not in cefi_keys]
        def avg_rate(keys: List[str]) -> float:
            vals: List[float] = []
            for k in keys:
                vals.extend(live[k]["rates"])  # simple average across provided terms
            return sum(vals) / len(vals) if vals else 0.0
        delta_bps = (avg_rate(cefi_keys) - avg_rate(defi_keys)) * 100.0
        payload["delta_bps"] = delta_bps
        return JSONResponse(content=payload)
    except Exception:
        return JSONResponse(status_code=502, content={"error": "Failed to fetch live yields"})


@app.get("/")
def dashboard():
    index_path = Path("frontend/index.html")
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


def _iso_from_unix(ts: float | int | None) -> str:
    try:
        if ts is None:
            raise ValueError()
        import datetime as _dt

        return _dt.datetime.fromtimestamp(float(ts), tz=_dt.timezone.utc).isoformat()
    except Exception:
        from datetime import datetime, timezone as _tz

        return datetime.now(_tz.utc).isoformat()


