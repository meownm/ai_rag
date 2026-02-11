export function Toggle({ value, onChange }: { value: boolean; onChange: (next: boolean) => void }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!value)}
      className={`h-6 w-12 rounded-full p-1 ${value ? 'bg-blue-600' : 'bg-slate-300'}`}
    >
      <span className={`block h-4 w-4 rounded-full bg-white transition ${value ? 'translate-x-6' : ''}`} />
    </button>
  );
}
