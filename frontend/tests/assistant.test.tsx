import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AssistantSection } from '../src/sections/AssistantSection';
import { suggestedQuestions } from '../src/data/suggestedQuestions';
import type { ChatResponse } from '../src/types/chat';

const MOCK_RESPONSE: ChatResponse = {
  answer: 'Mock grounded answer.\n- First supporting point\n- Second supporting point',
  citations: [
    {
      citation_id: 'C1',
      chunk_id: 'resume-professional-experience-001',
      source_name: 'Resume (placeholder)',
      source_type: 'RESUME',
      section: 'Professional Experience',
      experience_type: 'PROFESSIONAL',
      source_url: '/resume.pdf',
      excerpt: 'A bounded approved excerpt.',
    },
  ],
  suggested_questions: ['What technologies did he use?'],
  intent: 'PROFESSIONAL_EXPERIENCE',
  grounded: true,
  abstained: false,
  trace_id: 'trace-123',
};

function mockFetchOnce(body: unknown, init: { ok?: boolean; status?: number } = {}) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: init.ok ?? true,
    status: init.status ?? 200,
    json: async () => body,
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

describe('AI career assistant', () => {
  it('renders the welcome message and all five suggested questions', () => {
    mockFetchOnce(MOCK_RESPONSE);
    render(<AssistantSection />);

    expect(screen.getByText(/I’m Abhishek’s AI career assistant/i)).toBeInTheDocument();
    for (const question of suggestedQuestions) {
      expect(screen.getByRole('button', { name: question })).toBeInTheDocument();
    }
    expect(suggestedQuestions).toHaveLength(5);
  });

  it('submits a suggested question, collapses suggestions, and renders the answer', async () => {
    const user = userEvent.setup();
    const fetchMock = mockFetchOnce(MOCK_RESPONSE);
    render(<AssistantSection />);

    const question = suggestedQuestions[0]!;
    await user.click(screen.getByRole('button', { name: question }));

    expect(fetchMock).toHaveBeenCalledOnce();
    await waitFor(() => expect(screen.getByText('Mock grounded answer.')).toBeInTheDocument());

    expect(screen.getByText(question)).toBeInTheDocument();
    expect(screen.queryByText('Suggested questions')).not.toBeInTheDocument();
    expect(screen.getByText('Follow-up questions')).toBeInTheDocument();
  });

  it('sends the typed question when the form is submitted with Enter', async () => {
    const user = userEvent.setup();
    const fetchMock = mockFetchOnce(MOCK_RESPONSE);
    render(<AssistantSection />);

    const input = screen.getByLabelText(/ask about abhishek’s experience/i);
    await user.type(input, 'Where has he worked?{Enter}');

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    const [, requestInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(String(requestInit.body)).message).toBe('Where has he worked?');
  });

  it('limits the input to 500 characters', () => {
    mockFetchOnce(MOCK_RESPONSE);
    render(<AssistantSection />);

    const input = screen.getByLabelText(/ask about abhishek’s experience/i);
    expect(input).toHaveAttribute('maxlength', '500');
  });

  it('opens a citation drawer, closes it with Escape, and returns focus', async () => {
    const user = userEvent.setup();
    mockFetchOnce(MOCK_RESPONSE);
    render(<AssistantSection />);

    await user.click(screen.getByRole('button', { name: suggestedQuestions[0]! }));
    const citationButton = await screen.findByRole('button', { name: /^Source 1:/ });

    await user.click(citationButton);
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('A bounded approved excerpt.')).toBeInTheDocument();
    expect(within(dialog).getByText('Professional Experience')).toBeInTheDocument();

    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(citationButton).toHaveFocus();
  });

  it('shows the graceful unavailable message when the backend cannot be reached', async () => {
    const user = userEvent.setup();
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')));
    render(<AssistantSection />);

    await user.click(screen.getByRole('button', { name: suggestedQuestions[0]! }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/temporarily unavailable/i);
    expect(alert).toHaveTextContent(/still explore/i);
  });

  it('renders model output as text and never as HTML', async () => {
    const user = userEvent.setup();
    mockFetchOnce({
      ...MOCK_RESPONSE,
      answer: '<img src=x onerror="alert(1)">Injected',
      citations: [],
      suggested_questions: [],
    });
    const { container } = render(<AssistantSection />);

    await user.click(screen.getByRole('button', { name: suggestedQuestions[0]! }));

    await waitFor(() =>
      expect(screen.getByText(/<img src=x onerror="alert\(1\)">Injected/)).toBeInTheDocument(),
    );
    expect(container.querySelector('img')).toBeNull();
  });

  it('drops citations that use an unsafe URL scheme', async () => {
    const user = userEvent.setup();
    mockFetchOnce({
      ...MOCK_RESPONSE,
      citations: [{ ...MOCK_RESPONSE.citations[0]!, source_url: 'javascript:alert(1)' }],
    });
    render(<AssistantSection />);

    await user.click(screen.getByRole('button', { name: suggestedQuestions[0]! }));
    await user.click(await screen.findByRole('button', { name: /^Source 1:/ }));

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).queryByRole('link')).not.toBeInTheDocument();
  });

  it('renders an abstention notice when the assistant abstains', async () => {
    const user = userEvent.setup();
    mockFetchOnce({
      ...MOCK_RESPONSE,
      answer: 'I cannot answer that from approved sources.',
      citations: [],
      grounded: false,
      abstained: true,
    });
    render(<AssistantSection />);

    await user.click(screen.getByRole('button', { name: suggestedQuestions[0]! }));

    expect(
      await screen.findByText(/Not enough approved evidence was available/i),
    ).toBeInTheDocument();
  });

  it('records feedback locally without issuing a network request', async () => {
    const user = userEvent.setup();
    const fetchMock = mockFetchOnce(MOCK_RESPONSE);
    render(<AssistantSection />);

    await user.click(screen.getByRole('button', { name: suggestedQuestions[0]! }));
    const helpful = await screen.findByRole('button', { name: /as helpful/i });
    await user.click(helpful);

    expect(await screen.findByText(/thanks for the feedback/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledOnce();
  });
});
