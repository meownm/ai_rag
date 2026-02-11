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

export async function apiFetch<T>(path: string, init: RequestInit, schema: z.ZodType<T>): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
  });

  const payload = await response.json().catch(() => undefined);

  if (!response.ok) {
    const parsedError = ErrorEnvelopeSchema.safeParse(payload);
    throw new ApiError(parsedError.success ? parsedError.data.error.message : 'Request failed', response.status, payload);
  }

  return schema.parse(payload);
}
