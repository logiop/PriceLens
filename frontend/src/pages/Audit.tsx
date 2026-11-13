import { Activity } from "lucide-react";
import { api } from "../lib/api";
import { useFetch } from "../lib/hooks";
import { formatDate } from "../lib/format";
import { Loading, ErrorState, EmptyState } from "../components/States";
import { Badge } from "../components/Badge";

function toneFor(action: string): "green" | "red" | "amber" | "blue" | "indigo" | "slate" {
  if (action.endsWith(".delete") || action.endsWith(".member_remove")) return "red";
  if (action.startsWith("auth")) return "blue";
  if (action.startsWith("repricing")) return "green";
  if (action.startsWith("team")) return "indigo";
  return "slate";
}

const LABELS: Record<string, string> = {
  "auth.login": "Accesso",
  "auth.register": "Registrazione",
  "product.create": "Prodotto creato",
  "product.update": "Prodotto aggiornato",
  "product.delete": "Prodotto eliminato",
  "competitor.create": "Competitor creato",
  "competitor.update": "Competitor aggiornato",
  "competitor.delete": "Competitor eliminato",
  "repricing.apply": "Prezzo applicato",
  "collect.run": "Raccolta prezzi",
  "team.create": "Team creato",
  "team.rename": "Team rinominato",
  "team.member_add": "Membro aggiunto",
  "team.member_remove": "Membro rimosso",
};

export function Audit() {
  const { data, loading, error } = useFetch(() => api.audit(200));

  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} />;

  return (
    <div className="space-y-4 animate-fade-in-up">
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Activity size={16} />
        Registro delle azioni del team (append-only).
      </div>

      <div className="card overflow-hidden">
        {!data || data.length === 0 ? (
          <div className="p-6">
            <EmptyState title="Nessuna attività" hint="Le azioni del team compariranno qui." />
          </div>
        ) : (
          <ul className="divide-y divide-slate-50">
            {data.map((e) => (
              <li key={e.id} className="flex items-start gap-3 px-5 py-3">
                <div className="w-40 shrink-0 text-xs text-slate-400">{formatDate(e.created_at)}</div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={toneFor(e.action)}>{LABELS[e.action] ?? e.action}</Badge>
                    {e.detail && <span className="text-sm text-slate-700">{e.detail}</span>}
                  </div>
                  <div className="mt-0.5 text-[11px] text-slate-400">
                    {e.user_email ?? "sistema"}
                    {e.ip ? ` · ${e.ip}` : ""}
                    {e.entity ? ` · ${e.entity}#${e.entity_id ?? "—"}` : ""}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
