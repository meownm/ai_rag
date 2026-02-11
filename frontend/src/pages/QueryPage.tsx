import { useMemo, useState } from 'react';
import { ApiError } from '@/api/http';
import { RefusalSchema, type QueryResponse } from '@/api/schemas/query';
import { useQueryRag } from '@/hooks/useQueryRag';
import { useRoles } from '@/providers/RoleProvider';
import { UI_MODE } from '@/lib/env';
import { logEvent } from '@/lib/logger';
import type { ChatMessage } from '@/components/conversation/types';
import { AssistantMessage } from '@/components/conversation/AssistantMessage';
import { ClarificationModal } from '@/components/conversation/ClarificationModal';
import { ChunkPreviewModal } from '@/components/conversation/ChunkPreviewModal';

function buildClarificationOptions(query: string): string[] {
  const normalized = query.trim();
  if (normalized.includes(' или ')) {
    return normalized
      .split(' или ')
      .map((part) => part.trim())
      .filter(Boolean)
      .slice(0, 3);
  }
  if (normalized.includes('/')) {
    return normalized
      .split('/')
      .map((part) => part.trim())
      .filter(Boolean)
      .slice(0, 3);
  }
  return [];
}

function toAssistantPayload(response: QueryResponse) {
  const summary = response.answer.split('\n')[0] ?? response.answer;
  const details = response.answer;
  return {
    summary,
    details,
    sources: response.citations ?? [],
    debug: {
      interpretedQuery: summary,
      dynamicTopK: response.citations?.length ?? 0,
      chunksUsed: response.citations?.length ?? 0,
      coverageRatio: response.citations && response.citations.length > 0 ? 1 : 0,
      modelContextWindow: 8192,
      confidence: response.only_sources_verdict === 'PASS' ? 1 : 0,
    },
  };
}

function mapFriendlyError(error: ApiError): string {
  const payload = typeof error.payload === 'object' && error.payload ? (error.payload as Record<string, unknown>) : {};
  const code = payload.error && typeof payload.error === 'object' ? (payload.error as Record<string, unknown>).code : undefined;
  if (code === 'L-CONTEXT-OVERFLOW') {
    return 'Запрос слишком большой для контекстного окна. Уточните вопрос короче.';
  }
  if (error.message.toLowerCase().includes('network')) {
    return 'Сетевая ошибка. Проверьте соединение и попробуйте снова.';
  }
  return 'Не удалось получить ответ. Попробуйте повторить запрос позже.';
}

export function QueryPage() {
  const mutation = useQueryRag();
  const { roles } = useRoles();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [query, setQuery] = useState('');
  const [clarifications, setClarifications] = useState<string[]>([]);
  const [clarificationDepth, setClarificationDepth] = useState(0);
  const [selectedCitationIndex, setSelectedCitationIndex] = useState<number | null>(null);
  const [showSources, setShowSources] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [debugEnabled, setDebugEnabled] = useState(false);

  const canUseDebug = useMemo(() => UI_MODE === 'debug' || roles.includes('admin') || roles.includes('debug'), [roles]);
  const showDebug = canUseDebug && debugEnabled;

  const submitQuestion = async (nextQuery: string) => {
    const value = nextQuery.trim();
    if (!value) {
      return;
    }

    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'user', text: value }]);

    if (clarificationDepth < 2) {
      const options = buildClarificationOptions(value);
      if (options.length > 1) {
        setClarifications(options);
        setClarificationDepth((prev) => prev + 1);
        return;
      }
    }

    try {
      const response = await mutation.mutateAsync({ query: value });
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'assistant', assistant: toAssistantPayload(response), raw: response }]);
      setClarificationDepth(0);
    } catch (error) {
      const apiError = error as ApiError;
      const refusal = RefusalSchema.safeParse(apiError.payload);
      const text = refusal.success ? refusal.data.error.message : mapFriendlyError(apiError);
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'error', text }]);
      if (refusal.success) {
        logEvent('query_refusal', { correlationId: refusal.data.error.correlation_id });
      }
    }
  };

  const latestAssistant = [...messages].reverse().find((message) => message.role === 'assistant' && message.assistant?.sources)?.assistant;
  const selectedCitation = latestAssistant && selectedCitationIndex !== null ? latestAssistant.sources[selectedCitationIndex] : null;

  return (
    <div className="grid min-h-[calc(100vh-9rem)] grid-rows-[auto_1fr_auto] gap-3">
      <header className="flex flex-wrap items-center justify-between gap-2 rounded border bg-white p-3">
        <div className="text-lg font-semibold">Conversational RAG UI</div>
        <div className="flex gap-2">
          <button className="rounded border px-3 py-1 text-sm" onClick={() => setMessages([])}>
            New Dialog
          </button>
          <button className="rounded border px-3 py-1 text-sm" onClick={() => setShowSources((prev) => !prev)}>
            Sources
          </button>
          <button className="rounded border px-3 py-1 text-sm" onClick={() => setShowSettings((prev) => !prev)}>
            Settings
          </button>
        </div>
      </header>

      <main className="grid min-h-0 gap-3 md:grid-cols-[2fr_1fr]">
        <section className="space-y-2 overflow-y-auto rounded border bg-slate-50 p-3">
          {messages.map((message) => (
            <div key={message.id} className={message.role === 'user' ? 'ml-auto max-w-[80%] rounded-lg bg-indigo-600 p-3 text-white' : 'mr-auto max-w-[90%]'}>
              {message.role === 'assistant' && message.assistant ? (
                <AssistantMessage payload={message.assistant} showDebug={showDebug} onSourceClick={setSelectedCitationIndex} />
              ) : (
                <div>{message.text}</div>
              )}
            </div>
          ))}
          {mutation.isPending ? <div className="animate-pulse text-sm text-slate-500">Анализирую документы...</div> : null}
        </section>

        <aside className={`rounded border bg-white p-3 ${showSources ? 'block' : 'hidden md:block'}`}>
          <div className="text-sm font-semibold">Used documents</div>
          <ul className="mt-2 space-y-1 text-sm">
            {(latestAssistant?.sources ?? []).map((source, index) => (
              <li key={`${source.chunk_id}-${index}`}>
                <button className="text-left text-indigo-600 hover:underline" onClick={() => setSelectedCitationIndex(index)}>
                  {source.title}
                </button>
              </li>
            ))}
          </ul>
        </aside>
      </main>

      <footer className="rounded border bg-white p-3">
        <form
          className="flex gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            void submitQuestion(query);
            setQuery('');
          }}
        >
          <input
            className="w-full rounded border px-3 py-2"
            placeholder="Ask a question..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button className="rounded bg-indigo-600 px-4 py-2 text-white disabled:bg-indigo-300" disabled={mutation.isPending} type="submit">
            Send
          </button>
        </form>
      </footer>

      {showSettings ? (
        <div className="fixed right-4 top-20 z-30 rounded border bg-white p-3 shadow-lg">
          <label className="flex items-center gap-2 text-sm">
            <input disabled={!canUseDebug} type="checkbox" checked={debugEnabled} onChange={(event) => setDebugEnabled(event.target.checked)} />
            Debug transparency mode
          </label>
        </div>
      ) : null}

      <ClarificationModal
        options={clarifications}
        onSelect={(selection) => {
          setClarifications([]);
          if (selection) {
            void submitQuestion(selection);
          }
        }}
      />

      <ChunkPreviewModal citation={selectedCitation ?? null} onClose={() => setSelectedCitationIndex(null)} />
    </div>
  );
}
