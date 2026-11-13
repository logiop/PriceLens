import type { ReactNode } from "react";

type Tone = "green" | "red" | "amber" | "blue" | "slate" | "indigo";

const tones: Record<Tone, string> = {
  green: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  red: "bg-red-50 text-red-700 ring-red-600/20",
  amber: "bg-amber-50 text-amber-700 ring-amber-600/20",
  blue: "bg-sky-50 text-sky-700 ring-sky-600/20",
  slate: "bg-slate-100 text-slate-600 ring-slate-500/20",
  indigo: "bg-indigo-50 text-indigo-700 ring-indigo-600/20",
};

export function Badge({ tone = "slate", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function severityTone(severity: string): Tone {
  if (severity === "critical") return "red";
  if (severity === "warning") return "amber";
  return "blue";
}

export function severityLabel(severity: string): string {
  if (severity === "critical") return "Critico";
  if (severity === "warning") return "Avviso";
  return "Info";
}

export function positionTone(position: number | null | undefined): Tone {
  if (position === 1) return "green";
  if (position === 2) return "blue";
  if (position === 3) return "amber";
  return "slate";
}

export function positionLabel(position: number | null | undefined): string {
  if (position === null || position === undefined) return "—";
  return `${position}°`;
}
