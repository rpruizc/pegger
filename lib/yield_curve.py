from typing import Dict, List


def linear_interpolate(xs: List[float], ys: List[float], x_query: float) -> float:
    if not xs or not ys or len(xs) != len(ys):
        return 0.0
    if x_query <= xs[0]:
        return ys[0]
    if x_query >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if x_query <= xs[i]:
            x0, x1 = xs[i - 1], xs[i]
            y0, y1 = ys[i - 1], ys[i]
            t = (x_query - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return ys[-1]


def build_usdc_yield_curve(anchors: Dict[str, Dict[str, List[float]]] | None = None) -> Dict[str, object]:
    if anchors is None:
        anchors = {
            "Aave": {"days": [1, 7, 30], "rates": [4.1, 4.6, 5.2]},
            "Binance Earn": {"days": [1, 7, 30], "rates": [3.8, 4.3, 4.9]},
            "Compound": {"days": [1, 7, 30], "rates": [3.9, 4.4, 5.0]},
        }

    days = [1, 7, 30]
    avg_rates = []
    for i, _ in enumerate(days):
        vals = [v["rates"][i] for v in anchors.values()]
        avg_rates.append(sum(vals) / len(vals))

    curve_days = list(range(1, 31))
    curve_rates = [linear_interpolate(days, avg_rates, d) for d in curve_days]
    return {
        "symbol": "USDC",
        "anchors": anchors,
        "curve": {"days": curve_days, "rates": curve_rates},
    }


