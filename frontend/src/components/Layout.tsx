import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Activity,
  Bell,
  LayoutDashboard,
  LogOut,
  Package,
  RefreshCw,
  Sparkles,
  Store,
} from "lucide-react";
import { useState } from "react";
import { api } from "../lib/api";
import { getTeamId, setTeamId } from "../lib/auth";
import { useApp, useFetch } from "../lib/hooks";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/products", label: "Prodotti", icon: Package },
  { to: "/repricing", label: "Repricing", icon: Sparkles },
  { to: "/competitors", label: "Competitor", icon: Store },
  { to: "/alerts", label: "Alert", icon: Bell },
  { to: "/audit", label: "Attività", icon: Activity },
];

const TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/products": "Prodotti",
  "/repricing": "Repricing intelligente",
  "/competitors": "Competitor",
  "/alerts": "Alert",
  "/audit": "Registro attività",
};

export function Layout({ onLogout }: { onLogout: () => void }) {
  const location = useLocation();
  const { refresh } = useApp();
  const [collecting, setCollecting] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [activeTeam, setActiveTeam] = useState<number | null>(() => {
    const stored = getTeamId();
    return stored ? Number(stored) : null;
  });

  const { data: counts } = useFetch(() => api.alertCounts());
  const { data: user } = useFetch(() => api.me());
  const { data: teams } = useFetch(() => api.teams());

  const currentTeamId = activeTeam ?? teams?.[0]?.id ?? null;

  const title =
    TITLES[location.pathname] ??
    (location.pathname.startsWith("/products/") ? "Dettaglio prodotto" : "PriceLens");

  function handleTeamChange(teamId: number) {
    setTeamId(teamId);
    setActiveTeam(teamId);
    refresh();
  }

  async function handleCollect() {
    setCollecting(true);
    try {
      const res = await api.collect();
      setToast(
        `Raccolta completata: ${res.collected} rilevazioni, ${res.alerts_created} nuovi alert.`
      );
      refresh();
    } catch (err) {
      setToast(`Errore: ${(err as Error).message}`);
    } finally {
      setCollecting(false);
      setTimeout(() => setToast(null), 4000);
    }
  }

  return (
    <div className="flex h-full">
      <aside className="flex w-60 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="flex items-center gap-2.5 px-5 py-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600">
            <Sparkles size={18} className="text-white" />
          </div>
          <div>
            <div className="text-[15px] font-semibold leading-tight text-slate-900">PriceLens</div>
            <div className="text-[11px] leading-tight text-slate-400">Pricing Intelligence</div>
          </div>
        </div>

        <div className="px-3 pb-2">
          <label className="mb-1 block px-2 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
            Team
          </label>
          <select
            value={currentTeamId ?? ""}
            onChange={(e) => handleTeamChange(Number(e.target.value))}
            className="w-full rounded-lg border border-slate-200 bg-slate-50 px-2 py-1.5 text-xs font-medium text-slate-700 focus:border-indigo-500 focus:outline-none"
          >
            {(teams ?? []).map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>

        <nav className="mt-1 flex flex-1 flex-col gap-1 px-3">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`
              }
            >
              <Icon size={18} />
              <span className="flex-1">{label}</span>
              {to === "/alerts" && (counts?.unread ?? 0) > 0 && (
                <span className="rounded-full bg-red-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                  {counts!.unread}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-slate-100 px-4 py-3">
          <div className="mb-2 truncate px-1 text-xs text-slate-500">{user?.email ?? ""}</div>
          <button
            onClick={onLogout}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          >
            <LogOut size={16} />
            Esci
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white/80 px-6 py-3 backdrop-blur">
          <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
          <div className="flex items-center gap-3">
            <button
              onClick={handleCollect}
              disabled={collecting}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:opacity-60"
            >
              <RefreshCw size={16} className={collecting ? "animate-spin" : ""} />
              Raccogli prezzi
            </button>
            <NavLink
              to="/alerts"
              className="relative rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100"
              title="Alert"
            >
              <Bell size={19} />
              {(counts?.critical_unread ?? 0) > 0 && (
                <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-red-500" />
              )}
            </NavLink>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto px-6 py-6">
          <Outlet />
        </main>
      </div>

      {toast && (
        <div className="fixed bottom-5 right-5 z-50 max-w-sm rounded-xl bg-slate-900 px-4 py-3 text-sm text-white shadow-lg animate-fade-in-up">
          {toast}
        </div>
      )}
    </div>
  );
}
