import argparse
import json
from pathlib import Path
from typing import List

import uvicorn

from backend.api import app
from lib.amm import compute_slippage_summary
from lib.yield_curve import build_usdc_yield_curve
from lib.defillama import fetch_current_prices, fetch_usdc_lending_anchors


def print_table(headers: List[str], rows: List[List[object]]):
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    def fmt_row(r: List[object]) -> str:
        return " | ".join(str(c).ljust(col_widths[i]) for i, c in enumerate(r))

    print(fmt_row(headers))
    print("-+-".join("-" * w for w in col_widths))
    for r in rows:
        print(fmt_row(r))


def run_cli():
    # Live Peg snapshot
    symbols = ["USDC", "USDT", "DAI"]
    print("\nPeg Stability Snapshot (live)")
    price_map = fetch_current_prices(symbols)
    if not price_map:
        print("Prices unavailable (502)")
    else:
        from datetime import datetime, timezone

        ts_iso = datetime.now(timezone.utc).isoformat()
        rows = []
        for venue in ["Binance", "Curve"]:
            for s in symbols:
                meta = price_map.get(s)
                if not meta:
                    continue
                rows.append([venue, s, f"{meta['price']:.6f}", ts_iso])
        print_table(["Venue", "Symbol", "Price", "Timestamp"], rows)

    # Slippage
    print("\nLiquidity Simulator (Constant Product)")
    reserve_x = 50_000_000.0
    reserve_y = 50_000_000.0
    sizes = [1_000_000.0, 5_000_000.0, 10_000_000.0]
    slip_rows_dicts = compute_slippage_summary(reserve_x, reserve_y, sizes)
    slip_rows = [
        [
            f"{d['size']:.0f}",
            f"{d['out_amount']:.0f}",
            f"{d['execution_price']:.6f}",
            f"{d['slippage_bps']:.2f}",
        ]
        for d in slip_rows_dicts
    ]
    print_table(["Trade Size (in)", "Out Amount", "Exec Price (y/x)", "Slippage (bps)"], slip_rows)

    # Yield curve
    print("\nYield Curve (USDC, live)")
    live = fetch_usdc_lending_anchors()
    if not live:
        print("Yields unavailable (502)")
        return
    y = build_usdc_yield_curve(live)
    anchor_rows: List[List[object]] = []
    for platform, data in y["anchors"].items():
        d = ", ".join(f"{day}d" for day in data["days"])
        r = ", ".join(f"{rate:.2f}%" for rate in data["rates"])
        anchor_rows.append([platform, d, r])
    print_table(["Platform", "Terms", "Rates (APY)"], anchor_rows)
    curve_days = y["curve"]["days"]
    curve_rates = y["curve"]["rates"]
    sample = list(zip(curve_days[::6], curve_rates[::6]))
    sample_rows = [[f"{d}d", f"{r:.2f}%"] for d, r in sample]
    print("\nInterpolated (sampled):")
    print_table(["Day", "APY"], sample_rows)


def main():
    parser = argparse.ArgumentParser(description="Weal: Stablecoin Analytics Prototype")
    parser.add_argument("mode", choices=["web", "cli"], nargs="?", default="web")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.mode == "cli":
        run_cli()
    else:
        uvicorn.run("backend.api:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()


