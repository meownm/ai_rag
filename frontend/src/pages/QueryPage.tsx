import { useMemo, useState } from 'react';
import { ApiError } from '@/api/http';
import { RefusalSchema } from '@/api/schemas/query';
import { QueryInputCard } from '@/components/query/QueryInputCard';
import { AnswerPanel } from '@/components/query/AnswerPanel';
import { CitationsPanel } from '@/components/query/CitationsPanel';
import { SourcesTable } from '@/components/query/SourcesTable';
import { ScoringTraceDrawer } from '@/components/query/ScoringTraceDrawer';
import { PerformancePanel } from '@/components/query/PerformancePanel';
import { useQueryRag } from '@/hooks/useQueryRag';
import { useRoles } from '@/providers/RoleProvider';
import { UI_MODE } from '@/lib/env';
import { logEvent } from '@/lib/logger';

export function QueryPage() {
  const mutation = useQueryRag();
  const { roles } = useRoles();
  const [refusalMessage, setRefusalMessage] = useState<string>();

  const showDebug = useMemo(() => UI_MODE === 'debug' || roles.includes('admin') || roles.includes('debug'), [roles]);

  const onSubmit = async (query: string) => {
    setRefusalMessage(undefined);
    try {
      const response = await mutation.mutateAsync({ query });
      if (response.only_sources_verdict === 'FAIL') {
        const refusalPayload = parseRefusalAnswer(response.answer);
        if (refusalPayload?.success) {
          setRefusalMessage(refusalPayload.data.error.message);
          logEvent('query_refusal', { correlationId: refusalPayload.data.error.correlation_id });
        }
      }
    } catch (error) {
      const apiError = error as ApiError;
      const refusal = RefusalSchema.safeParse(apiError.payload);
      if (refusal.success) {
        setRefusalMessage(refusal.data.error.message);
        logEvent('query_refusal', { correlationId: refusal.data.error.correlation_id });
      } else {
        logEvent('query_error', { message: apiError.message });
      }
    }
  };

  return (
    <div className="space-y-4">
      <QueryInputCard onSubmit={onSubmit} loading={mutation.isPending} />
      {mutation.isPending ? <div className="animate-pulse rounded border bg-white p-4">Loading answer...</div> : null}
      <AnswerPanel answer={mutation.data?.answer} refusal={refusalMessage} />
      <CitationsPanel citations={mutation.data?.citations ?? []} />
      <SourcesTable citations={mutation.data?.citations ?? []} />
      {showDebug ? <ScoringTraceDrawer citations={mutation.data?.citations ?? []} /> : null}
      {showDebug ? <PerformancePanel timings={mutation.data?.timings_ms} /> : null}
    </div>
  );
}

function parseRefusalAnswer(answer: string) {
  try {
    const parsed = JSON.parse(answer) as unknown;
    return RefusalSchema.safeParse(parsed);
  } catch {
    return null;
  }
}
