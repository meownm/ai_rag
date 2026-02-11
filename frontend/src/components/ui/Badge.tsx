export function Badge({ value }: { value: string }) {
  const color = value === 'done' || value === 'PASS' ? 'bg-emerald-100 text-emerald-800' : value === 'error' || value === 'FAIL' ? 'bg-red-100 text-red-800' : 'bg-slate-100 text-slate-700';
  return <span className={`rounded px-2 py-1 text-xs font-semibold ${color}`}>{value}</span>;
}
