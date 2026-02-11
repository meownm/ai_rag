import { z } from 'zod';

export const ErrorSchema = z.object({
  code: z.string(),
  message: z.string(),
  details: z.record(z.unknown()).optional(),
  correlation_id: z.string(),
  retryable: z.boolean(),
  timestamp: z.string(),
});

export const ErrorEnvelopeSchema = z.object({
  error: ErrorSchema,
});

export type ErrorEnvelope = z.infer<typeof ErrorEnvelopeSchema>;
