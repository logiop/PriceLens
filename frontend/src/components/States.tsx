import { Loader2 } from "lucide-react";

export function Loading({ label = "Caricamento…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-400">
      <Loader2 size={18} className="animate-spin" />
      {label}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      Impossibile caricare i dati: {message}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 rounded-xl border border-dashed border-slate-300 py-14 text-center">
      <div className="text-sm font-medium text-slate-600">{title}</div>
      {hint && <div className="text-xs text-slate-400">{hint}</div>}
    </div>
  );
}
