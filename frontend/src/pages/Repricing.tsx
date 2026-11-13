import { useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, Sparkles } from "lucide-react";
import { api } from "../lib/api";
import { useApp, useFetch } from "../lib/hooks";
import { formatPct, formatPrice } from "../lib/format";
import { Loading, ErrorState, EmptyState } from "../components/States";
import { Badge } from "../components/Badge";
import { PriceDelta } from "../components/PriceDelta";
import type { RepricingRecommendation } from "../types";

export function Repricing() {
  const { refresh } = useApp();
  const [applied, setApplied] = useState<Set<number>>(new Set());

  const { data, loading, error } = useFetch(() => api.repricingPreview());

  if (loading) return <Loading />;
  if (error || !data) return <ErrorState message={error ?? "dati non disponibili"} />;

  const recs = data.recommendations;

  async function handleApply(r: RepricingRecommendation) {
    try {
      await api.applyRepricing(r.product_id, r.suggested_price);
      setApplied((s) => new Set(s).add(r.product_id));
      refresh();
    } catch (err) {
      alert((err as Error).message);
    }
  }

  const actionable = recs.filter((r) => Math.abs(r.delta_pct) >= 0.5);

  return (
    <div className="space-y-5 animate-fade-in-up">
      <div className="card flex items-center justify-between p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
            <Sparkles size={20} />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-900">Repricing intelligente</h2>
            <p className="text-sm text-slate-500">
              {actionable.length} prodotti con un prezzo suggerito diverso dall'attuale.
            </p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-slate-400">Impatto potenziale totale</div>
          <div className="text-lg font-semibold tabular-nums text-slate-900">
            {formatPrice(data.total_potential_margin_impact)}
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        {recs.length === 0 ? (
          <div className="p-6">
            <EmptyState title="Nessun prodotto da valutare" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left">
                  <th className="table-head px-5 py-3">Prodotto</th>
                  <th className="table-head px-5 py-3">Prezzo attuale</th>
                  <th className="table-head px-5 py-3">Suggerito</th>
                  <th className="table-head px-5 py-3">Δ</th>
                  <th className="table-head px-5 py-3">Margine</th>
                  <th className="table-head px-5 py-3">Razionale</th>
                  <th className="table-head px-5 py-3" />
                </tr>
              </thead>
              <tbody>
                {recs.map((r) => {
                  const isApplied = applied.has(r.product_id) || Math.abs(r.delta_pct) < 0.01;
                  return (
                    <tr key={r.product_id} className="border-b border-slate-50 hover:bg-slate-50/60">
                      <td className="px-5 py-3">
                        <Link to={`/products/${r.product_id}`} className="font-medium text-slate-800 hover:text-indigo-600">
                          {r.name}
                        </Link>
                        <div className="text-xs text-slate-400">{r.sku}</div>
                      </td>
                      <td className="px-5 py-3 tabular-nums text-slate-600">{formatPrice(r.current_price)}</td>
                      <td className="px-5 py-3 font-semibold tabular-nums text-slate-900">
                        {formatPrice(r.suggested_price)}
                      </td>
                      <td className="px-5 py-3">
                        <PriceDelta value={r.delta_pct} />
                      </td>
                      <td className="px-5 py-3 tabular-nums text-emerald-600">{formatPct(r.margin_pct, false)}</td>
                      <td className="max-w-xs px-5 py-3 text-xs leading-relaxed text-slate-500">{r.rationale}</td>
                      <td className="px-5 py-3 text-right">
                        {isApplied ? (
                          <Badge tone="green">Applicato</Badge>
                        ) : (
                          <button
                            onClick={() => handleApply(r)}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700"
                          >
                            <CheckCircle2 size={14} /> Applica
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
