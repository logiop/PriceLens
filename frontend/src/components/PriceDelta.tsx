import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { formatPct } from "../lib/format";

export function PriceDelta({ value, className = "" }: { value: number | null | undefined; className?: string }) {
  if (value === null || value === undefined) {
    return <span className={`text-slate-400 ${className}`}>—</span>;
  }
  const up = value > 0;
  const flat = Math.abs(value) < 0.005;
  const color = flat ? "text-slate-500" : up ? "text-red-600" : "text-emerald-600";
  const Icon = flat ? Minus : up ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={`inline-flex items-center gap-0.5 font-medium tabular-nums ${color} ${className}`}>
      <Icon size={14} strokeWidth={2.5} />
      {formatPct(value)}
    </span>
  );
}
