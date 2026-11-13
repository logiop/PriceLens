import { useState } from "react";
import type { Product, Strategy } from "../types";

const STRATEGIES: Array<{ value: Strategy; label: string }> = [
  { value: "match_min", label: "Allinea al minimo" },
  { value: "undercut", label: "Sottoquotazione (2%)" },
  { value: "margin_protected", label: "Margine protetto" },
  { value: "premium", label: "Premium" },
];

type FormState = {
  sku: string;
  name: string;
  brand: string;
  category: string;
  cost_price: string;
  current_price: string;
  msrp: string;
  map_price: string;
  strategy: Strategy;
  min_margin_pct: string;
};

function initialState(initial?: Product): FormState {
  return {
    sku: initial?.sku ?? "",
    name: initial?.name ?? "",
    brand: initial?.brand ?? "",
    category: initial?.category ?? "",
    cost_price: initial ? String(initial.cost_price) : "",
    current_price: initial ? String(initial.current_price) : "",
    msrp: initial?.msrp != null ? String(initial.msrp) : "",
    map_price: initial?.map_price != null ? String(initial.map_price) : "",
    strategy: initial?.strategy ?? "margin_protected",
    min_margin_pct: initial ? String(initial.min_margin_pct) : "15",
  };
}

export function ProductForm({
  initial,
  onSubmit,
  submitting,
}: {
  initial?: Product;
  onSubmit: (payload: Record<string, unknown>) => void;
  submitting?: boolean;
}) {
  const [form, setForm] = useState<FormState>(() => initialState(initial));

  const set = (key: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      sku: form.sku.trim(),
      name: form.name.trim(),
      brand: form.brand.trim(),
      category: form.category.trim(),
      cost_price: form.cost_price === "" ? 0 : Number(form.cost_price),
      current_price: Number(form.current_price),
      msrp: form.msrp === "" ? null : Number(form.msrp),
      map_price: form.map_price === "" ? null : Number(form.map_price),
      strategy: form.strategy,
      min_margin_pct: Number(form.min_margin_pct),
    });
  }

  const field =
    "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500";
  const label = "mb-1 block text-xs font-medium text-slate-600";

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={label}>Nome prodotto *</label>
          <input className={field} value={form.name} onChange={set("name")} required placeholder="iPhone 15 128GB" />
        </div>
        <div>
          <label className={label}>SKU *</label>
          <input className={field} value={form.sku} onChange={set("sku")} required placeholder="APP-IP15-128" />
        </div>
        <div>
          <label className={label}>Brand</label>
          <input className={field} value={form.brand} onChange={set("brand")} placeholder="Apple" />
        </div>
        <div>
          <label className={label}>Categoria</label>
          <input className={field} value={form.category} onChange={set("category")} placeholder="Smartphone" />
        </div>
        <div>
          <label className={label}>Costo (€) *</label>
          <input className={field} type="number" step="0.01" min="0" value={form.cost_price} onChange={set("cost_price")} required />
        </div>
        <div>
          <label className={label}>Prezzo di vendita (€) *</label>
          <input className={field} type="number" step="0.01" min="0" value={form.current_price} onChange={set("current_price")} required />
        </div>
        <div>
          <label className={label}>MSRP (€)</label>
          <input className={field} type="number" step="0.01" min="0" value={form.msrp} onChange={set("msrp")} placeholder="Prezzo consigliato" />
        </div>
        <div>
          <label className={label}>MAP (€)</label>
          <input className={field} type="number" step="0.01" min="0" value={form.map_price} onChange={set("map_price")} placeholder="Prezzo minimo pubblicizzato" />
        </div>
        <div>
          <label className={label}>Strategia di repricing</label>
          <select className={field} value={form.strategy} onChange={set("strategy")}>
            {STRATEGIES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={label}>Margine minimo (%)</label>
          <input className={field} type="number" step="0.1" min="0" max="100" value={form.min_margin_pct} onChange={set("min_margin_pct")} />
        </div>
      </div>
      <div className="flex justify-end gap-2 pt-1">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
        >
          {initial ? "Salva modifiche" : "Crea prodotto"}
        </button>
      </div>
    </form>
  );
}
