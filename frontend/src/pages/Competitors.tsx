import { useState } from "react";
import { Globe, Plus, Store, Trash2 } from "lucide-react";
import { api } from "../lib/api";
import { useApp, useFetch } from "../lib/hooks";
import { Loading, ErrorState } from "../components/States";
import { Badge } from "../components/Badge";
import { Modal } from "../components/Modal";

export function Competitors() {
  const { refresh } = useApp();
  const [showCreate, setShowCreate] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const { data: competitors, loading, error } = useFetch(() => api.competitors());

  const [form, setForm] = useState({
    name: "",
    domain: "",
    type: "retailer",
    price_source_type: "simulated",
    base_ratio: "1.0",
    url: "",
  });

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const config =
        form.price_source_type === "simulated"
          ? { base_ratio: Number(form.base_ratio) || 1.0, volatility: 0.02, promo_prob: 0.06, stockout_prob: 0.02 }
          : { url: form.url };
      await api.createCompetitor({
        name: form.name,
        domain: form.domain,
        type: form.type as "retailer" | "marketplace",
        price_source_type: form.price_source_type as "simulated" | "url",
        price_source_config: config,
      });
      setShowCreate(false);
      setForm({ name: "", domain: "", type: "retailer", price_source_type: "simulated", base_ratio: "1.0", url: "" });
      refresh();
    } catch (err) {
      alert((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: number, name: string) {
    if (!confirm(`Eliminare il competitor "${name}"?`)) return;
    try {
      await api.deleteCompetitor(id);
      refresh();
    } catch (err) {
      alert((err as Error).message);
    }
  }

  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} />;

  const field =
    "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500";
  const label = "mb-1 block text-xs font-medium text-slate-600";

  return (
    <div className="space-y-4 animate-fade-in-up">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          {competitors?.length ?? 0} competitor monitorati · fonti simulate o URL live
        </p>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          <Plus size={16} /> Nuovo competitor
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {competitors?.map((c) => (
          <div key={c.id} className="card p-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
                  <Store size={18} />
                </div>
                <div>
                  <div className="font-semibold text-slate-900">{c.name}</div>
                  <div className="flex items-center gap-1 text-xs text-slate-400">
                    <Globe size={12} /> {c.domain || "—"}
                  </div>
                </div>
              </div>
              <button
                onClick={() => handleDelete(c.id, c.name)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
              >
                <Trash2 size={15} />
              </button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge tone={c.type === "marketplace" ? "indigo" : "slate"}>
                {c.type === "marketplace" ? "Marketplace" : "Retailer"}
              </Badge>
              <Badge tone={c.price_source_type === "url" ? "amber" : "blue"}>
                {c.price_source_type === "url" ? "Fonte live" : "Simulato"}
              </Badge>
              <Badge tone={c.active ? "green" : "slate"}>{c.active ? "Attivo" : "Inattivo"}</Badge>
            </div>
            <div className="mt-3 border-t border-slate-100 pt-3 text-xs text-slate-500">
              {c.products_tracked} prodotti tracciati
            </div>
          </div>
        ))}
      </div>

      <Modal open={showCreate} title="Nuovo competitor" onClose={() => setShowCreate(false)}>
        <form onSubmit={handleCreate} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={label}>Nome *</label>
              <input className={field} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required placeholder="Amazon" />
            </div>
            <div>
              <label className={label}>Dominio</label>
              <input className={field} value={form.domain} onChange={(e) => setForm({ ...form, domain: e.target.value })} placeholder="amazon.it" />
            </div>
            <div>
              <label className={label}>Tipo</label>
              <select className={field} value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                <option value="retailer">Retailer</option>
                <option value="marketplace">Marketplace</option>
              </select>
            </div>
            <div>
              <label className={label}>Fonte prezzo</label>
              <select
                className={field}
                value={form.price_source_type}
                onChange={(e) => setForm({ ...form, price_source_type: e.target.value })}
              >
                <option value="simulated">Simulata</option>
                <option value="url">URL live</option>
              </select>
            </div>
          </div>
          {form.price_source_type === "simulated" ? (
            <div>
              <label className={label}>Posizionamento prezzo (rapporto vs tuo prezzo)</label>
              <input className={field} type="number" step="0.01" min="0.5" max="1.5" value={form.base_ratio} onChange={(e) => setForm({ ...form, base_ratio: e.target.value })} />
              <p className="mt-1 text-xs text-slate-400">1.0 = stesso prezzo, 0.9 = 10% più economico, 1.05 = 5% più caro.</p>
            </div>
          ) : (
            <div>
              <label className={label}>URL pagina prodotto</label>
              <input className={field} value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} placeholder="https://…/prodotto" />
              <p className="mt-1 text-xs text-slate-400">PriceLens cercherà il prezzo nella pagina (JSON-LD o pattern comuni).</p>
            </div>
          )}
          <div className="flex justify-end">
            <button type="submit" disabled={submitting} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60">
              Crea competitor
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
