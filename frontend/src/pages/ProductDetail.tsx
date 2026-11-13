import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  Pencil,
  TrendingDown,
  TrendingUp,
  Wand2,
} from "lucide-react";
import { api } from "../lib/api";
import { useApp, useFetch } from "../lib/hooks";
import { formatPct, formatPrice, relativeTime } from "../lib/format";
import { Loading, ErrorState } from "../components/States";
import { Badge, positionTone, positionLabel } from "../components/Badge";
import { PriceChart } from "../components/PriceChart";
import { PriceDelta } from "../components/PriceDelta";
import { Modal } from "../components/Modal";
import { ProductForm } from "../components/ProductForm";

export function ProductDetail() {
  const { id } = useParams();
  const productId = Number(id);
  const { refresh } = useApp();
  const [days, setDays] = useState(30);
  const [showEdit, setShowEdit] = useState(false);
  const [applying, setApplying] = useState(false);

  const { data, loading, error } = useFetch(() => api.product(productId), [productId]);
  const { data: history } = useFetch(() => api.productHistory(productId, days), [productId, days]);

  if (loading) return <Loading />;
  if (error || !data) return <ErrorState message={error ?? "prodotto non trovato"} />;

  const rec = data.recommendation;

  async function handleApply() {
    if (!rec) return;
    setApplying(true);
    try {
      await api.applyRepricing(rec.product_id, rec.suggested_price);
      refresh();
    } catch (err) {
      alert((err as Error).message);
    } finally {
      setApplying(false);
    }
  }

  async function handleEdit(payload: Record<string, unknown>) {
    try {
      await api.updateProduct(data!.id, payload as Parameters<typeof api.updateProduct>[1]);
      setShowEdit(false);
      refresh();
    } catch (err) {
      alert((err as Error).message);
    }
  }

  const stockCount = data.competitors.filter((c) => c.stock_status === "in_stock").length;

  return (
    <div className="space-y-5 animate-fade-in-up">
      <div className="flex items-start justify-between">
        <div>
          <Link
            to="/products"
            className="mb-3 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800"
          >
            <ArrowLeft size={16} /> Prodotti
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-slate-900">{data.name}</h1>
            <Badge tone={positionTone(data.position)}>{positionLabel(data.position)}</Badge>
            <Badge tone="slate">{data.category}</Badge>
          </div>
          <div className="mt-1 text-sm text-slate-500">
            {data.brand} · SKU {data.sku}
          </div>
        </div>
        <button
          onClick={() => setShowEdit(true)}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <Pencil size={15} /> Modifica
        </button>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: "Tuo prezzo", value: formatPrice(data.current_price), sub: `Costo ${formatPrice(data.cost_price)}` },
          { label: "Min competitor", value: formatPrice(data.min_price), sub: "Più economico" },
          { label: "Max competitor", value: formatPrice(data.max_price), sub: "Più caro" },
          { label: "Competitor in stock", value: `${stockCount}/${data.competitors.length}`, sub: "Disponibilità" },
        ].map((k) => (
          <div key={k.label} className="card p-4">
            <div className="text-xs font-medium text-slate-500">{k.label}</div>
            <div className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{k.value}</div>
            <div className="text-xs text-slate-400">{k.sub}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        {/* Chart */}
        <div className="card p-5 xl:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Storico prezzi</h2>
              <p className="text-xs text-slate-500">Confronto con i competitor nel tempo</p>
            </div>
            <div className="flex gap-1">
              {[7, 30, 60].map((d) => (
                <button
                  key={d}
                  onClick={() => setDays(d)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                    days === d ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {d} giorni
                </button>
              ))}
            </div>
          </div>
          <PriceChart series={history ?? []} currentPrice={data.current_price} />
        </div>

        {/* Repricing recommendation */}
        <div className="card flex flex-col p-5">
          <div className="mb-3 flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
              <Wand2 size={16} />
            </div>
            <h2 className="text-sm font-semibold text-slate-900">Prezzo consigliato</h2>
          </div>
          {rec ? (
            <>
              <div className="rounded-xl bg-slate-50 p-4">
                <div className="text-xs text-slate-500">Prezzo suggerito</div>
                <div className="text-3xl font-semibold tabular-nums text-slate-900">
                  {formatPrice(rec.suggested_price)}
                </div>
                <div className="mt-1 flex items-center gap-2">
                  <span className="text-xs text-slate-500">Margine stimato</span>
                  <span className="text-xs font-semibold text-emerald-600">{formatPct(rec.margin_pct, false)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">Rispetto ad oggi</span>
                  <PriceDelta value={rec.delta_pct} className="text-xs" />
                </div>
              </div>
              <p className="mt-3 text-xs leading-relaxed text-slate-500">{rec.rationale}</p>
              <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-400">
                <span className="rounded-md bg-slate-100 px-2 py-1">Floor: {formatPrice(rec.floor)}</span>
                <span className="rounded-md bg-slate-100 px-2 py-1">Ceiling: {formatPrice(rec.ceiling)}</span>
              </div>
              <button
                onClick={handleApply}
                disabled={applying || Math.abs(rec.delta_pct) < 0.01}
                className="mt-4 inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                <CheckCircle2 size={16} />
                Applica nuovo prezzo
              </button>
            </>
          ) : (
            <p className="text-sm text-slate-400">Nessuna raccomandazione disponibile.</p>
          )}
        </div>
      </div>

      {/* Competitor table */}
      <div className="card overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-3">
          <h2 className="text-sm font-semibold text-slate-900">Confronto competitor</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left">
                <th className="table-head px-5 py-3">Competitor</th>
                <th className="table-head px-5 py-3">Prezzo</th>
                <th className="table-head px-5 py-3">Differenza vs te</th>
                <th className="table-head px-5 py-3">Variazione</th>
                <th className="table-head px-5 py-3">Stock</th>
                <th className="table-head px-5 py-3">Aggiornato</th>
              </tr>
            </thead>
            <tbody>
              {data.competitors.map((c) => {
                const diff = c.price != null ? c.price - data.current_price : null;
                return (
                  <tr key={c.competitor_id} className="border-b border-slate-50 hover:bg-slate-50/60">
                    <td className="px-5 py-3">
                      <div className="font-medium text-slate-800">{c.competitor_name}</div>
                      <div className="text-xs text-slate-400">{c.domain}</div>
                    </td>
                    <td className="px-5 py-3 font-semibold tabular-nums text-slate-900">
                      {formatPrice(c.price)}
                    </td>
                    <td className="px-5 py-3">
                      {diff == null ? (
                        <span className="text-slate-300">—</span>
                      ) : diff > 0 ? (
                        <span className="inline-flex items-center gap-1 text-red-600">
                          <TrendingUp size={14} /> +{formatPrice(diff)}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-emerald-600">
                          <TrendingDown size={14} /> {formatPrice(diff)}
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      <PriceDelta value={c.change_pct} />
                    </td>
                    <td className="px-5 py-3">
                      {c.stock_status === "in_stock" ? (
                        <Badge tone="green">Disponibile</Badge>
                      ) : (
                        <Badge tone="red">Esaurito</Badge>
                      )}
                    </td>
                    <td className="px-5 py-3 text-xs text-slate-400">{relativeTime(c.captured_at ?? "")}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <Modal open={showEdit} title={`Modifica ${data.name}`} onClose={() => setShowEdit(false)} wide>
        <ProductForm initial={data} onSubmit={handleEdit} />
      </Modal>

      <div className="text-xs text-slate-400">
        Alert MAP/MSRP e variazioni per questo prodotto sono disponibili nella sezione{" "}
        <Link to="/alerts" className="text-indigo-600 hover:underline">
          Alert
        </Link>
        .{" "}
        {data.open_alerts > 0 && (
          <Badge tone="red">{data.open_alerts} aperti</Badge>
        )}
      </div>
    </div>
  );
}
