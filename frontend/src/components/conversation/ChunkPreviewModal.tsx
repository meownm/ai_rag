import type { Citation } from '@/api/schemas/query';

export function ChunkPreviewModal({ citation, onClose }: { citation: Citation | null; onClose: () => void }) {
  if (!citation) {
    return null;
  }
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/30">
      <div className="w-full max-w-2xl rounded-lg bg-white p-4 shadow-xl">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">{citation.title}</h3>
          <button className="text-sm text-slate-500 hover:underline" onClick={onClose}>
            Закрыть
          </button>
        </div>
        <p className="mt-3 whitespace-pre-wrap rounded bg-yellow-50 p-3 text-sm">{citation.snippet}</p>
      </div>
    </div>
  );
}
