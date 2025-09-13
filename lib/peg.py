import random
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Tuple

Stablecoin = str
Venue = str


class PegDataStore:
    """
    Thread-safe in-memory store for synthetic stablecoin prices by venue.
    Prices are simple random walks around $1.00.
    """

    def __init__(self, symbols: List[Stablecoin], venues: List[Venue]):
        self.symbols = symbols
        self.venues = venues
        self._lock = threading.Lock()
        self._prices: Dict[Tuple[Venue, Stablecoin], float] = {}
        now = self._now_iso()
        self._timestamps: Dict[Tuple[Venue, Stablecoin], str] = {}
        for v in venues:
            for s in symbols:
                base = 1.0 + random.uniform(-0.0015, 0.0015)
                self._prices[(v, s)] = base
                self._timestamps[(v, s)] = now

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def random_walk(self):
        with self._lock:
            now = self._now_iso()
            for key, price in list(self._prices.items()):
                drift = (1.0 - price) * 0.05
                shock = random.uniform(-0.0008, 0.0008)
                new_price = max(0.95, min(1.05, price + drift + shock))
                self._prices[key] = new_price
                self._timestamps[key] = now

    def snapshot(self) -> List[Dict[str, object]]:
        with self._lock:
            rows: List[Dict[str, object]] = []
            for (venue, symbol), price in self._prices.items():
                rows.append(
                    {
                        "venue": venue,
                        "symbol": symbol,
                        "price": round(price, 6),
                        "timestamp": self._timestamps[(venue, symbol)],
                    }
                )
            return rows


def start_price_background_updater(store: PegDataStore, interval_seconds: float = 3.0) -> threading.Thread:
    def _loop():
        while True:
            store.random_walk()
            time.sleep(interval_seconds)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t


