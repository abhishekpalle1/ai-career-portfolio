import { describe, expect, it, vi } from 'vitest';
import { normalizeChatResponse, postChatMessage } from '../src/api/careerAssistantApi';
import { ApiError } from '../src/types/chat';

describe('normalizeChatResponse', () => {
  it('fills in safe defaults for a minimal payload', () => {
    const result = normalizeChatResponse({ answer: 'Hello' });

    expect(result).toEqual({
      answer: 'Hello',
      citations: [],
      suggested_questions: [],
      intent: 'UNKNOWN',
      grounded: false,
      abstained: false,
      trace_id: '',
    });
  });

  it('rejects a payload without an answer', () => {
    expect(() => normalizeChatResponse({})).toThrow(ApiError);
  });

  it('removes duplicate citation ids', () => {
    const citation = { citation_id: 'C1', source_url: '/resume.pdf' };
    const result = normalizeChatResponse({ answer: 'a', citations: [citation, citation] });

    expect(result.citations).toHaveLength(1);
  });

  it('strips unsafe citation URL schemes', () => {
    for (const unsafe of ['javascript:alert(1)', 'data:text/html,x', 'file:///etc/passwd']) {
      const result = normalizeChatResponse({
        answer: 'a',
        citations: [{ citation_id: 'C1', source_url: unsafe }],
      });
      expect(result.citations[0]!.source_url).toBe('');
    }
  });

  it('caps follow-up questions at three', () => {
    const result = normalizeChatResponse({
      answer: 'a',
      suggested_questions: ['one', 'two', 'three', 'four'],
    });
    expect(result.suggested_questions).toHaveLength(3);
  });
});

describe('postChatMessage', () => {
  it('raises an unavailable error when the network call fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    await expect(postChatMessage({ message: 'hi' })).rejects.toMatchObject({
      kind: 'unavailable',
    });
  });

  it('raises an invalid error for a 422 response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 422 }));
    await expect(postChatMessage({ message: 'hi' })).rejects.toMatchObject({ kind: 'invalid' });
  });

  it('raises an unavailable error for a 500 response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    await expect(postChatMessage({ message: 'hi' })).rejects.toMatchObject({
      kind: 'unavailable',
    });
  });
});
