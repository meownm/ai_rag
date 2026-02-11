import { z } from 'zod';
import { ErrorEnvelopeSchema } from './common';

export const JobStatusSchema = z.enum(['queued', 'processing', 'retrying', 'done', 'error', 'canceled', 'expired']);

export const JobAcceptedResponseSchema = z.object({
  job_id: z.string(),
  job_status: JobStatusSchema,
});

export const JobStatusResponseSchema = z.object({
  job_id: z.string(),
  tenant_id: z.string(),
  job_type: z.string(),
  job_status: JobStatusSchema,
  requested_by: z.string(),
  started_at: z.string(),
  finished_at: z.string().nullable().optional(),
  error: ErrorEnvelopeSchema.optional(),
});

export type JobAcceptedResponse = z.infer<typeof JobAcceptedResponseSchema>;
export type JobStatusResponse = z.infer<typeof JobStatusResponseSchema>;
