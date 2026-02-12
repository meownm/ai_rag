import type { Citation, QueryResponse } from '@/api/schemas/query';

export type MessageRole = 'user' | 'assistant' | 'error';

export type AssistantPayload = {
  summary: string;
  details: string;
  sources: Citation[];
  debug?: {
    interpretedQuery?: string;
    dynamicTopK?: number;
    chunksUsed?: number;
    coverageRatio?: number;
    modelContextWindow?: number;
    confidence?: number;
    agentTrace?: Array<{ stage: string; latencyMs: number }>;
  };
};

export type ChatMessage = {
  id: string;
  role: MessageRole;
  text?: string;
  assistant?: AssistantPayload;
  raw?: QueryResponse;
};
