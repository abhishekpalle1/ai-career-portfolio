import { ApiError } from '../types/chat';
import type { ChatRequestPayload, ChatResponse, Citation } from '../types/chat';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(
  /\/$/,
  '',
);

const REQUEST_TIMEOUT_MS = 20_000;

export const MAX_INPUT_CHARACTERS = 500;

const SAFE_URL_PATTERN = /^(https?:|mailto:|\/)/i;

export async function postChatMessage(payload: ChatRequestPayload): Promise<ChatResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
  } catch {
    throw new ApiError('unavailable', 'The AI assistant could not be reached.');
  } finally {
    clearTimeout(timeout);
  }

  if (response.status === 422 || response.status === 400) {
    throw new ApiError('invalid', 'That question could not be processed. Please rephrase it.');
  }
  if (!response.ok) {
    throw new ApiError('unavailable', 'The AI assistant is temporarily unavailable.');
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new ApiError('unexpected', 'The AI assistant returned an unreadable response.');
  }

  return normalizeChatResponse(body);
}

/** Defensive normalization: the UI never trusts the response shape blindly. */
export function normalizeChatResponse(body: unknown): ChatResponse {
  if (typeof body !== 'object' || body === null) {
    throw new ApiError('unexpected', 'The AI assistant returned an unreadable response.');
  }

  const raw = body as Record<string, unknown>;
  if (typeof raw.answer !== 'string' || raw.answer.length === 0) {
    throw new ApiError('unexpected', 'The AI assistant returned an unreadable response.');
  }

  return {
    answer: raw.answer,
    citations: normalizeCitations(raw.citations),
    suggested_questions: asStringArray(raw.suggested_questions).slice(0, 3),
    intent: typeof raw.intent === 'string' ? raw.intent : 'UNKNOWN',
    grounded: raw.grounded === true,
    abstained: raw.abstained === true,
    trace_id: typeof raw.trace_id === 'string' ? raw.trace_id : '',
  };
}

function normalizeCitations(value: unknown): Citation[] {
  if (!Array.isArray(value)) return [];

  const seen = new Set<string>();
  const citations: Citation[] = [];

  for (const item of value) {
    if (typeof item !== 'object' || item === null) continue;
    const raw = item as Record<string, unknown>;
    const citationId = typeof raw.citation_id === 'string' ? raw.citation_id : '';
    if (!citationId || seen.has(citationId)) continue;

    const sourceUrl = typeof raw.source_url === 'string' ? raw.source_url : '';
    seen.add(citationId);
    citations.push({
      citation_id: citationId,
      chunk_id: typeof raw.chunk_id === 'string' ? raw.chunk_id : '',
      source_name: typeof raw.source_name === 'string' ? raw.source_name : 'Source',
      source_type: (typeof raw.source_type === 'string'
        ? raw.source_type
        : 'RESUME') as Citation['source_type'],
      section: typeof raw.section === 'string' ? raw.section : '',
      experience_type: (typeof raw.experience_type === 'string'
        ? raw.experience_type
        : 'GENERAL') as Citation['experience_type'],
      // Unsafe schemes (javascript:, data:, file:) are dropped, not rendered.
      source_url: SAFE_URL_PATTERN.test(sourceUrl) ? sourceUrl : '',
      excerpt: typeof raw.excerpt === 'string' ? raw.excerpt : '',
    });
  }

  return citations;
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === 'string' && item.length > 0);
}
