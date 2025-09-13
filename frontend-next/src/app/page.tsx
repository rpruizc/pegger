"use client";

import { useEffect, useMemo, useState } from "react";

type PegRow = { venue: string; symbol: string; price: number; timestamp: string };
type SlippageRow = { size: number; out_amount: number; execution_price: number; slippage_bps: number };
type YieldData = { anchors: Record<string, { days: number[]; rates: number[] }>; curve: { days: number[]; rates: number[] } };

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8001";

export default function Home() {
  const [intervalSec, setIntervalSec] = useState<number>(3);
  const [peg, setPeg] = useState<PegRow[]>([]);
  const [slip, setSlip] = useState<SlippageRow[]>([]);
  const [yieldData, setYieldData] = useState<YieldData | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [pegRes, slipRes, yRes] = await Promise.all([
        fetch(`${BACKEND}/peg`).then((r) => r.json()),
        fetch(`${BACKEND}/slippage`).then((r) => r.json()),
        fetch(`${BACKEND}/yield`).then((r) => r.json()),
      ]);
      setPeg((pegRes?.data as PegRow[]) || []);
      setSlip((slipRes?.summary as SlippageRow[]) || []);
      setYieldData(yRes as YieldData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  useEffect(() => {
    if (intervalSec <= 0) return;
    const id = setInterval(fetchAll, intervalSec * 1000);
    return () => clearInterval(id);
  }, [intervalSec]);

  const pegSorted = useMemo(
    () => [...peg].sort((a, b) => a.symbol.localeCompare(b.symbol) || a.venue.localeCompare(b.venue)),
    [peg]
  );

  return (
    <main style={{ padding: 20, color: "#e6e6e6", background: "#0e0f13", minHeight: "100vh" }}>
      <h1 style={{ fontSize: 18, marginBottom: 8 }}>Pegger • Live Stablecoin Analytics</h1>
      <div style={{ color: "#9aa4bf", marginBottom: 16 }}>FastAPI backend: {BACKEND}</div>
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <label>Refresh every (sec):</label>
        <input
          type="number"
          value={intervalSec}
          min={0}
          step={1}
          onChange={(e) => setIntervalSec(parseInt(e.target.value || "0", 10))}
          style={{ width: 80, padding: 6, background: "#0f1422", color: "#e6e6e6", border: "1px solid #22252e", borderRadius: 6 }}
        />
        <button onClick={fetchAll} style={{ background: "#2b5cff", color: "#fff", border: 0, borderRadius: 6, padding: "8px 10px" }}>
          {loading ? "Refreshing…" : "Refresh now"}
        </button>
      </div>

      <section style={{ display: "grid", gap: 16 }}>
        <div style={{ background: "#131826", border: "1px solid #22252e", borderRadius: 10, padding: 14 }}>
          <div style={{ color: "#9aa4bf", marginBottom: 8 }}>Peg Monitor (USDC/USDT/DAI)</div>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: 8 }}>Symbol</th>
                <th style={{ textAlign: "left", padding: 8 }}>Venue</th>
                <th style={{ textAlign: "left", padding: 8 }}>Price</th>
                <th style={{ textAlign: "left", padding: 8 }}>Updated</th>
              </tr>
            </thead>
            <tbody>
              {pegSorted.map((r, i) => (
                <tr key={i}>
                  <td style={{ padding: 8, borderBottom: "1px solid #242938" }}>{r.symbol}</td>
                  <td style={{ padding: 8, borderBottom: "1px solid #242938" }}>{r.venue}</td>
                  <td style={{ padding: 8, borderBottom: "1px solid #242938" }}>{r.price.toFixed(6)}</td>
                  <td style={{ padding: 8, borderBottom: "1px solid #242938" }}>{new Date(r.timestamp).toLocaleTimeString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={{ background: "#131826", border: "1px solid #22252e", borderRadius: 10, padding: 14 }}>
          <div style={{ color: "#9aa4bf", marginBottom: 8 }}>Liquidity Simulator (Constant Product)</div>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: 8 }}>Trade Size (in)</th>
                <th style={{ textAlign: "left", padding: 8 }}>Out Amount</th>
                <th style={{ textAlign: "left", padding: 8 }}>Exec Price (y/x)</th>
                <th style={{ textAlign: "left", padding: 8 }}>Slippage (bps)</th>
              </tr>
            </thead>
            <tbody>
              {slip.map((d, i) => (
                <tr key={i}>
                  <td style={{ padding: 8, borderBottom: "1px solid #242938" }}>${d.size.toLocaleString()}</td>
                  <td style={{ padding: 8, borderBottom: "1px solid #242938" }}>${d.out_amount.toLocaleString()}</td>
                  <td style={{ padding: 8, borderBottom: "1px solid #242938" }}>{d.execution_price.toFixed(6)}</td>
                  <td style={{ padding: 8, borderBottom: "1px solid #242938" }}>{d.slippage_bps.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={{ background: "#131826", border: "1px solid #22252e", borderRadius: 10, padding: 14 }}>
          <div style={{ color: "#9aa4bf", marginBottom: 8 }}>Yield Curve (USDC)</div>
          {yieldData && (
            <>
              <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: 12 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: "left", padding: 8 }}>Platform</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Terms</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(yieldData.anchors).map(([name, v]) => (
                    <tr key={name}>
                      <td style={{ padding: 8, borderBottom: "1px solid #242938" }}>{name}</td>
                      <td style={{ padding: 8, borderBottom: "1px solid #242938" }}>{v.days.map((d, i) => `${d}d: ${v.rates[i].toFixed(2)}%`).join(" · ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ color: "#9aa4bf" }}>
                Interpolated 1–30d: {yieldData.curve.rates.slice(0, 6).map((r) => r.toFixed(2) + "%").join(" · ")} …
              </div>
            </>
          )}
        </div>
      </section>
    </main>
  );
}
