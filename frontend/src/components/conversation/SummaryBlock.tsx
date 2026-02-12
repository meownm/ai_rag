export function SummaryBlock({ summary }: { summary: string }) {
  return (
    <section aria-label="Summary block">
      <div className="text-xs uppercase tracking-wide text-slate-500">Summary</div>
      <div className="mt-1 font-medium text-slate-900">{summary}</div>
    </section>
  );
}
