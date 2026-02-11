import { z } from 'zod';

export const ScoreBreakdownSchema = z.object({
  lex_score: z.number(),
  vec_score: z.number(),
  rerank_score: z.number(),
  boosts: z.record(z.number()),
  final_score: z.number(),
});

export const CitationSchema = z.object({
  chunk_id: z.string(),
  document_id: z.string(),
  title: z.string(),
  url: z.string(),
  snippet: z.string(),
  score_breakdown: ScoreBreakdownSchema.optional(),
  file_path: z.string().optional(),
  headings_path: z.array(z.string()).optional(),
});

export const QueryResponseSchema = z.object({
  answer: z.string(),
  only_sources_verdict: z.enum(['PASS', 'FAIL']),
  citations: z.array(CitationSchema).optional().default([]),
  correlation_id: z.string(),
  timings_ms: z
    .object({
      t_parse_ms: z.number().optional(),
      t_lexical_ms: z.number().optional(),
      t_vector_ms: z.number().optional(),
      t_rerank_ms: z.number().optional(),
      t_total_ms: z.number().optional(),
    })
    .optional(),
});

export const RefusalSchema = z.object({
  error: z
    .object({
      code: z.literal('ONLY_SOURCES_VIOLATION'),
      message: z.string(),
      correlation_id: z.string(),
      retryable: z.boolean(),
      timestamp: z.string(),
      details: z.record(z.unknown()).optional(),
    })
    .strict(),
});

export type Citation = z.infer<typeof CitationSchema>;
export type QueryResponse = z.infer<typeof QueryResponseSchema>;
export type RefusalResponse = z.infer<typeof RefusalSchema>;
