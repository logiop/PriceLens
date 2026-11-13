import { useState } from "react";
import { Link } from "react-router-dom";
import { BellOff, CheckCheck, CheckCircle2, FileDown } from "lucide-react";
import { api, downloadExport } from "../lib/api";
import { useApp, useFetch } from "../lib/hooks";
import { relativeTime } from "../lib/format";
import { Loading, ErrorState, EmptyState } from "../components/States";
import { Badge, severityTone, severityLabel } from "../components/Badge";

export function Alerts() {
  const { refresh } = useApp();
  const [filter, setFilter] = useState<"all" | "unread" | "critical">("all");

  const { data: alerts, loading, error } = useFetch(
    () =>
      api.alerts({
        unread: filter === "unread" ? true : undefined,
        severity: filter === "critical" ? "critical" : undefined,
      }),
    [filter]
  );

  async function handleMarkRead(id: number) {
    await api.markAlertRead(id);
    refresh();
  }

  async function handleMarkAll() {
    await api.markAllRead();
    refresh();
  }

  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} />;

  return (
    <div className="space-y-4 animate-fade-in-up">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex gap-1 rounded-lg bg-slate-100 p-1">
          {[
            { key: "all", label: "Tutti" },
            { key: "unread", label: "Da leggere" },
            { key: "critical", label: "Critici" },
          ].map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key as typeof filter)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium ${
                filter === f.key ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-800"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <button
          onClick={() => downloadExport(api.exportAlertsUrl("csv"))}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <FileDown size={16} /> CSV
        </button>
        <button
          onClick={() => downloadExport(api.exportAlertsUrl("xlsx"))}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <FileDown size={16} /> Excel
        </button>
        <button
          onClick={handleMarkAll}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <CheckCheck size={16} /> Segna tutti come letti
        </button>
      </div>

      <div className="card overflow-hidden">
        {alerts?.length === 0 ? (
          <div className="p-6">
            <EmptyState title="Nessun alert" hint="Tutto sotto controllo." />
          </div>
        ) : (
          <ul className="divide-y divide-slate-50">
            {alerts?.map((a) => (
              <li key={a.id} className={`flex items-start gap-3 px-5 py-3.5 ${a.read ? "opacity-60" : ""}`}>
                <span
                  className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                    a.read ? "bg-slate-200" : a.severity === "critical" ? "bg-red-500" : "bg-amber-400"
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <div className="text-sm leading-snug text-slate-800">{a.message}</div>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                    <Badge tone={severityTone(a.severity)}>{severityLabel(a.severity)}</Badge>
                    {a.product_name && (
                      <Link to={`/products/${a.product_id}`} className="text-indigo-600 hover:underline">
                        {a.product_name}
                      </Link>
                    )}
                    <span>·</span>
                    <span>{relativeTime(a.created_at)}</span>
                  </div>
                </div>
                {!a.read && (
                  <button
                    onClick={() => handleMarkRead(a.id)}
                    className="inline-flex shrink-0 items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-slate-500 hover:bg-slate-100"
                    title="Segna come letto"
                  >
                    <CheckCircle2 size={14} />
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {alerts && alerts.length > 0 && (
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <BellOff size={14} /> Gli alert vengono generati automaticamente ad ogni raccolta prezzi.
        </div>
      )}
    </div>
  );
}
