import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { FileDown, Plus, Search, Trash2 } from "lucide-react";
import { api, downloadExport } from "../lib/api";
import { useApp, useFetch } from "../lib/hooks";
import { formatPrice } from "../lib/format";
import { Loading, ErrorState, EmptyState } from "../components/States";
import { Badge, positionTone, positionLabel } from "../components/Badge";
import { PriceDelta } from "../components/PriceDelta";
import { PriceIndex } from "../components/PriceIndex";
import { Modal } from "../components/Modal";
import { ProductForm } from "../components/ProductForm";

export function Products() {
  const { refresh } = useApp();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const { data: products, loading, error } = useFetch(() => api.products());
  const { data: categories } = useFetch(() => api.categories());

  const filtered = useMemo(() => {
    if (!products) return [];
    return products.filter((p) => {
      if (category && p.category !== category) return false;
      if (search) {
        const q = search.toLowerCase();
        const hay = `${p.name} ${p.sku} ${p.brand}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [products, search, category]);

  async function handleCreate(payload: Record<string, unknown>) {
    setSubmitting(true);
    try {
      await api.createProduct(payload as Parameters<typeof api.createProduct>[0]);
      setShowCreate(false);
      refresh();
    } catch (err) {
      alert((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: number, name: string) {
    if (!confirm(`Eliminare "${name}"?`)) return;
    try {
      await api.deleteProduct(id);
      refresh();
    } catch (err) {
      alert((err as Error).message);
    }
  }

  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} />;

  return (
    <div className="space-y-4 animate-fade-in-up">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Cerca per nome, SKU o brand…"
            className="w-72 rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
        >
          <option value="">Tutte le categorie</option>
          {(categories ?? []).map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <div className="flex-1" />
        <button
          onClick={() => downloadExport(api.exportProductsUrl("csv"))}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <FileDown size={16} /> CSV
        </button>
        <button
          onClick={() => downloadExport(api.exportProductsUrl("xlsx"))}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <FileDown size={16} /> Excel
        </button>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          <Plus size={16} />
          Nuovo prodotto
        </button>
      </div>

      <div className="card overflow-hidden">
        {filtered.length === 0 ? (
          <div className="p-6">
            <EmptyState title="Nessun prodotto trovato" hint="Modifica i filtri o crea un nuovo prodotto." />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left">
                  <th className="table-head px-4 py-3">Prodotto</th>
                  <th className="table-head px-4 py-3">Tuo prezzo</th>
                  <th className="table-head px-4 py-3">Min competitor</th>
                  <th className="table-head px-4 py-3">Max competitor</th>
                  <th className="table-head px-4 py-3">Posizione</th>
                  <th className="table-head px-4 py-3">Indice</th>
                  <th className="table-head px-4 py-3">Variazione</th>
                  <th className="table-head px-4 py-3">Alert</th>
                  <th className="table-head px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((p) => (
                  <tr key={p.id} className="border-b border-slate-50 transition-colors hover:bg-slate-50/60">
                    <td className="px-4 py-3">
                      <Link to={`/products/${p.id}`} className="block">
                        <div className="font-medium text-slate-800 hover:text-indigo-600">{p.name}</div>
                        <div className="text-xs text-slate-400">
                          {p.brand} · {p.sku}
                        </div>
                      </Link>
                    </td>
                    <td className="px-4 py-3 font-semibold tabular-nums text-slate-900">
                      {formatPrice(p.current_price)}
                    </td>
                    <td className="px-4 py-3 tabular-nums text-emerald-600">
                      {formatPrice(p.min_price)}
                    </td>
                    <td className="px-4 py-3 tabular-nums text-slate-600">
                      {formatPrice(p.max_price)}
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={positionTone(p.position)}>{positionLabel(p.position)}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      <PriceIndex value={p.price_index} />
                    </td>
                    <td className="px-4 py-3">
                      <PriceDelta value={p.last_change_pct} />
                    </td>
                    <td className="px-4 py-3">
                      {p.open_alerts > 0 ? (
                        <Badge tone="red">{p.open_alerts}</Badge>
                      ) : (
                        <span className="text-slate-300">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleDelete(p.id, p.name)}
                        className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                        title="Elimina"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Modal open={showCreate} title="Nuovo prodotto" onClose={() => setShowCreate(false)} wide>
        <ProductForm onSubmit={handleCreate} submitting={submitting} />
      </Modal>
    </div>
  );
}
