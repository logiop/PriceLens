import { useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HistorySeries } from "../types";
import { formatPrice } from "../lib/format";

const PALETTE = ["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6", "#f97316"];

export function PriceChart({
  series,
  currentPrice,
  height = 320,
}: {
  series: HistorySeries[];
  currentPrice?: number | null;
  height?: number;
}) {
  const { data, keys } = useMemo(() => {
    const timeSet = new Map<number, Record<string, number | null>>();
    for (const s of series) {
      for (const p of s.points) {
        if (p.price === null) continue;
        const t = new Date(p.captured_at).getTime();
        if (!timeSet.has(t)) timeSet.set(t, {});
        timeSet.get(t)![s.competitor_name] = p.price;
      }
    }
    const times = [...timeSet.keys()].sort((a, b) => a - b);
    const keys = series.map((s) => s.competitor_name);
    const data = times.map((t) => ({ time: t, ...timeSet.get(t)! }));
    return { data, keys };
  }, [series]);

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-slate-400">
        Nessuno storico disponibile
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" vertical={false} />
        <XAxis
          dataKey="time"
          type="number"
          domain={["dataMin", "dataMax"]}
          tickFormatter={(t) => new Intl.DateTimeFormat("it-IT", { day: "2-digit", month: "short" }).format(t)}
          tick={{ fontSize: 11, fill: "#94a3b8" }}
          tickLine={false}
          axisLine={{ stroke: "#e2e8f0" }}
        />
        <YAxis
          width={56}
          tickFormatter={(v: number) => `€${v}`}
          tick={{ fontSize: 11, fill: "#94a3b8" }}
          tickLine={false}
          axisLine={false}
          domain={["auto", "auto"]}
        />
        <Tooltip
          labelFormatter={(t) => new Intl.DateTimeFormat("it-IT", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(t as number)}
          formatter={(value) => (value == null ? "—" : formatPrice(Number(value)))}
          contentStyle={{ borderRadius: 10, border: "1px solid #e9ebf0", fontSize: 12 }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {currentPrice != null && (
          <ReferenceLine
            y={currentPrice}
            stroke="#0f172a"
            strokeDasharray="4 4"
            label={{ value: "Tuo prezzo", position: "insideBottomRight", fontSize: 11, fill: "#64748b" }}
          />
        )}
        {keys.map((key, i) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            stroke={PALETTE[i % PALETTE.length]}
            strokeWidth={2}
            dot={false}
            connectNulls
            activeDot={{ r: 4 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
