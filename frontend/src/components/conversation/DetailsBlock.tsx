export function DetailsBlock({ details }: { details: string }) {
  return (
    <section aria-label="Details block">
      <div className="mt-3 text-xs uppercase tracking-wide text-slate-500">Details</div>
      <div className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{details}</div>
    </section>
  );
}
