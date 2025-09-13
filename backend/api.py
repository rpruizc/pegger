from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from lib.amm import compute_slippage_summary
from lib.yield_curve import build_usdc_yield_curve
from lib.defillama import fetch_current_prices, fetch_stablecoin_prices, fetch_usdc_lending_anchors
import json
from pathlib import Path


SYMBOLS: List[str] = ["USDC", "USDT", "DAI"]
VENUES: List[str] = ["Binance", "Curve"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # No background tasks; live-only data
    yield


app = FastAPI(title="Weal: Stablecoin Analytics (Prototype)", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")


@app.get("/peg")
def get_peg_snapshot():
    # Live-only DefiLlama prices
    try:
        price_map = fetch_current_prices(["USDC", "USDT", "DAI"])  # coingecko-based
        if not price_map:
            stable_map = fetch_stablecoin_prices(["USDC", "USDT", "DAI"])  # stablecoins API
            price_map = {s: {"price": p, "timestamp": 0} for s, p in stable_map.items()}

        if not price_map:
            return JSONResponse(status_code=502, content={"error": "Live prices unavailable"})

        rows = []
        for v in VENUES:
            for s in SYMBOLS:
                meta = price_map.get(s)
                if not meta:
                    continue
                rows.append(
                    {
                        "venue": v,
                        "symbol": s,
                        "price": round(float(meta["price"]), 6),
                        "timestamp": _iso_from_unix(meta.get("timestamp")),
                    }
                )
        return JSONResponse(content={"data": rows})
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": "Failed to fetch live prices"})


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


@app.get("/yield")
def get_yield_curve():
    # Live-only anchors
    try:
        live = fetch_usdc_lending_anchors()
        if not live:
            return JSONResponse(status_code=502, content={"error": "Live yields unavailable"})
        return JSONResponse(content=build_usdc_yield_curve(live))
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


