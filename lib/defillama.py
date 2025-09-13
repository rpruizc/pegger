from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import httpx


COINS_BASE = "https://coins.llama.fi"
YIELDS_BASE = "https://yields.llama.fi"
STABLECOINS_BASE = "https://stablecoins.llama.fi"


SYMBOL_TO_COINGECKO: Dict[str, str] = {
    "USDC": "usd-coin",
    "USDT": "tether",
    "DAI": "dai",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_current_prices(symbols: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Fetch current prices using DefiLlama coins API via coingecko IDs.
    Returns mapping: symbol -> {price: float, timestamp: int}.
    """
    tokens: List[str] = []
    for s in symbols:
        cid = SYMBOL_TO_COINGECKO.get(s.upper())
        if cid:
            tokens.append(f"coingecko:{cid}")

    if not tokens:
        return {}

    coins_param = ",".join(tokens)
    url = f"{COINS_BASE}/prices/current/{coins_param}"
    with httpx.Client(timeout=5.0) as client:
        r = client.get(url)
        r.raise_for_status()
        data = r.json().get("coins", {})

    result: Dict[str, Dict[str, float]] = {}
    for s in symbols:
        cid = SYMBOL_TO_COINGECKO.get(s.upper())
        if not cid:
            continue
        key = f"coingecko:{cid}"
        if key in data:
            entry = data[key]
            result[s.upper()] = {
                "price": float(entry.get("price", 0.0)),
                "timestamp": float(entry.get("timestamp", time.time())),
            }
    return result


def fetch_stablecoin_prices(symbols: List[str]) -> Dict[str, float]:
    """
    Alternate source: /stablecoins?includePrices=true, aggregate price per symbol.
    Returns mapping symbol -> price (float) if available.
    """
    url = f"{STABLECOINS_BASE}/stablecoins?includePrices=true"
    with httpx.Client(timeout=8.0) as client:
        r = client.get(url)
        r.raise_for_status()
        body = r.json()
    out: Dict[str, float] = {}
    for asset in body.get("peggedAssets", []):
        sym = str(asset.get("symbol", "")).upper()
        if sym in {s.upper() for s in symbols}:
            price = asset.get("price")
            if isinstance(price, (int, float)):
                out[sym] = float(price)
    return out


def fetch_usdc_lending_anchors() -> Dict[str, Dict[str, List[float]]]:
    """
    Fetch current USDC APYs for a few lending platforms from /pools.
    Returns anchors dict like { platform: { days: [1,7,30], rates: [apy, apy, apy] } }.
    """
    url = f"{YIELDS_BASE}/pools"
    with httpx.Client(timeout=10.0) as client:
        r = client.get(url)
        r.raise_for_status()
        data = r.json().get("data", [])

    # Preferred projects and synonyms
    preferred = {
        "aave": "Aave",
        "aave-v3": "Aave V3",
        "compound": "Compound",
        "compound-v3": "Compound V3",
    }

    # Filter for USDC supply/lend pools on main chains and select top by TVL
    candidates: Dict[str, Tuple[float, float]] = {}  # display -> (apy, tvl)
    for p in data:
        symbol = str(p.get("symbol", "")).upper()
        if symbol != "USDC":
            continue
        project = str(p.get("project", "")).lower()
        display = preferred.get(project)
        if not display:
            continue
        apy = p.get("apy") or p.get("apyBase")
        tvl = p.get("tvlUsd", 0.0)
        if isinstance(apy, (int, float)) and isinstance(tvl, (int, float)):
            # Keep the highest TVL instance per display name
            prev = candidates.get(display)
            if prev is None or tvl > prev[1]:
                candidates[display] = (float(apy), float(tvl))

    anchors: Dict[str, Dict[str, List[float]]] = {}
    for display, (apy, _tvl) in candidates.items():
        anchors[display] = {"days": [1, 7, 30], "rates": [float(apy), float(apy), float(apy)]}
    return anchors


