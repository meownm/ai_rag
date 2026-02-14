import { z } from 'zod';
import { API_BASE_URL } from '@/lib/env';
import { ErrorEnvelopeSchema } from './schemas/common';

export class ApiError extends Error {
  status: number;
  payload?: unknown;

  constructor(message: string, status: number, payload?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

async function readResponsePayload(response: Response): Promise<unknown> {
  const contentType = response.headers?.get?.('content-type')?.toLowerCase() ?? '';

  if (contentType.includes('application/json')) {
    return response.json().catch(() => undefined);
  }

  if (!contentType) {
    const clone = response.clone?.();
    const clonedJson = clone?.json ? await clone.json().catch(() => undefined) : undefined;
    if (clonedJson !== undefined) {
      return clonedJson;
    }

    const directJson = response.json ? await response.json().catch(() => undefined) : undefined;
    if (directJson !== undefined) {
      return directJson;
    }
  }

  const rawText = response.text ? await response.text().catch(() => '') : '';
  return rawText.trim() ? rawText : undefined;
}

export async function apiFetch<T>(path: string, init: RequestInit, schema: z.ZodType<T>): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
  });

  const payload = await readResponsePayload(response);

  if (!response.ok) {
    const parsedError = ErrorEnvelopeSchema.safeParse(payload);
    throw new ApiError(parsedError.success ? parsedError.data.error.message : 'Request failed', response.status, payload);
  }

  return schema.parse(payload);
}
