import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Gauge,
  Package,
  Store,
} from "lucide-react";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../lib/api";
import { useFetch } from "../lib/hooks";
import { formatPrice, relativeTime } from "../lib/format";
import { StatCard } from "../components/StatCard";
import { ErrorState, Loading } from "../components/States";
import { PriceDelta } from "../components/PriceDelta";
import { severityTone, Badge } from "../components/Badge";

export function Dashboard() {
  const { data, loading, error } = useFetch(() => api.dashboard());

  if (loading) return <Loading />;
  if (error || !data) return <ErrorState message={error ?? "dati non disponibili"} />;

  const { kpis, top_movers, price_index_distribution, recent_alerts } = data;

  const chartData = price_index_distribution
    .filter((d) => d.price_index !== null)
    .map((d) => ({ name: d.name, sku: d.sku, index: d.price_index ?? 0 }))
    .sort((a, b) => a.index - b.index);

  return (
    <div className="space-y-5 animate-fade-in-up">
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <StatCard icon={Package} label="Prodotti monitorati" value={kpis.products} accent="indigo" />
        <StatCard icon={Store} label="Competitor attivi" value={kpis.competitors} accent="indigo" />
        <StatCard
          icon={AlertTriangle}
          label="Alert aperti"
          value={kpis.open_alerts}
          sub={kpis.critical_alerts > 0 ? `${kpis.critical_alerts} critici` : undefined}
          accent="red"
        />
        <StatCard
          icon={Gauge}
          label="Indice di prezzo medio"
          value={kpis.avg_price_index ?? "—"}
          sub="Più alto = più competitivo"
          accent="emerald"
        />
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        {/* Price index distribution */}
        <div className="card p-5 xl:col-span-1">
          <h2 className="mb-1 text-sm font-semibold text-slate-900">Indice di competitività</h2>
          <p className="mb-4 text-xs text-slate-500">Posizionamento prezzo per prodotto (0–100)</p>
          {chartData.length === 0 ? (
            <div className="py-10 text-center text-sm text-slate-400">Nessun dato</div>
          ) : (
            <ResponsiveContainer width="100%" height={chartData.length * 34 + 30}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 24 }}>
                <XAxis type="number" domain={[0, 100]} hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={120}
                  tick={{ fontSize: 11, fill: "#64748b" }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  formatter={(v) => [`${v}`, "Indice"]}
                  contentStyle={{ borderRadius: 10, border: "1px solid #e9ebf0", fontSize: 12 }}
                />
                <Bar dataKey="index" radius={[0, 4, 4, 0]} barSize={16}>
                  {chartData.map((d) => (
                    <Cell
                      key={d.sku}
                      fill={d.index >= 70 ? "#10b981" : d.index >= 40 ? "#f59e0b" : "#ef4444"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Top movers */}
        <div className="card p-5 xl:col-span-1">
          <h2 className="mb-4 text-sm font-semibold text-slate-900">Maggiore variazione</h2>
          <div className="space-y-1">
            {top_movers.length === 0 && (
              <div className="py-10 text-center text-sm text-slate-400">Nessuna variazione</div>
            )}
            {top_movers.map((m) => (
              <Link
                key={m.product_id}
                to={`/products/${m.product_id}`}
                className="flex items-center gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-slate-50"
              >
                <div
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
                    (m.change_pct ?? 0) > 0
                      ? "bg-red-50 text-red-600"
                      : "bg-emerald-50 text-emerald-600"
                  }`}
                >
                  {(m.change_pct ?? 0) > 0 ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-slate-800">{m.name}</div>
                  <div className="text-xs text-slate-400">{m.brand}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-semibold tabular-nums text-slate-900">
                    {formatPrice(m.current_price)}
                  </div>
                  <PriceDelta value={m.change_pct} className="text-xs" />
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Recent alerts */}
        <div className="card p-5 xl:col-span-1">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Alert recenti</h2>
            <Link to="/alerts" className="text-xs font-medium text-indigo-600 hover:underline">
              Vedi tutti
            </Link>
          </div>
          <div className="space-y-3">
            {recent_alerts.length === 0 && (
              <div className="py-10 text-center text-sm text-slate-400">Nessun alert</div>
            )}
            {recent_alerts.map((a) => (
              <div key={a.id} className="flex gap-2.5">
                <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-slate-300" />
                <div className="min-w-0">
                  <div className="text-[13px] leading-snug text-slate-700">{a.message}</div>
                  <div className="mt-0.5 flex items-center gap-2 text-[11px] text-slate-400">
                    <Badge tone={severityTone(a.severity)}>{a.severity}</Badge>
                    <span>{relativeTime(a.created_at)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
