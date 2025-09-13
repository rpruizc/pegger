from typing import Dict, List


def compute_constant_product_trade_output(reserve_in: float, reserve_out: float, amount_in: float) -> float:
    if amount_in <= 0:
        return 0.0
    if reserve_in <= 0 or reserve_out <= 0:
        return 0.0
    k = reserve_in * reserve_out
    new_reserve_in = reserve_in + amount_in
    new_reserve_out = k / new_reserve_in
    amount_out = reserve_out - new_reserve_out
    return max(0.0, amount_out)


def compute_slippage_summary(reserve_x: float, reserve_y: float, trade_sizes: List[float]) -> List[Dict[str, float]]:
    if reserve_x <= 0 or reserve_y <= 0:
        return []
    mid_price = reserve_y / reserve_x
    rows: List[Dict[str, float]] = []
    for size in trade_sizes:
        out = compute_constant_product_trade_output(reserve_x, reserve_y, size)
        exec_price = out / size if size > 0 else 0.0
        slippage = 0.0
        if exec_price > 0:
            slippage = (mid_price - exec_price) / mid_price * 10000.0
        rows.append(
            {
                "size": float(size),
                "out_amount": float(out),
                "execution_price": float(exec_price),
                "slippage_bps": float(slippage),
            }
        )
    return rows


