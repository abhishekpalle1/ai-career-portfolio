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
  it('renders the left-aligned Ask My AI heading and supporting sentence', () => {
    mockFetchOnce(MOCK_RESPONSE);
    const { container } = render(<AssistantSection />);

    expect(screen.getByRole('heading', { level: 2, name: 'Ask My AI' })).toBeInTheDocument();
    expect(
      screen.getByText('Get instant answers about my experience, projects, and more.'),
    ).toBeInTheDocument();
    expect(container.querySelector('.assistant__inner')).not.toBeNull();
    expect(container.textContent).not.toMatch(/career evidence assistant/i);
    expect(container.querySelector('.section-label')).toBeNull();
  });

  it('renders a compact white header with aria-hidden decorative circles', () => {
    mockFetchOnce(MOCK_RESPONSE);
    const { container } = render(<AssistantSection />);
    const header = container.querySelector('.chat-panel__header') as HTMLElement;

    expect(within(header).getByText('AI Career Assistant')).toBeInTheDocument();
    expect(within(header).getByText('Grounded in approved career materials')).toBeInTheDocument();
    expect(container.querySelector('.chat-panel__dots')).toHaveAttribute('aria-hidden', 'true');
    expect(container.querySelectorAll('.chat-panel__dots i')).toHaveLength(3);
  });

  it('renders the introductory message with an AI badge and all five questions', () => {
    mockFetchOnce(MOCK_RESPONSE);
    const { container } = render(<AssistantSection />);

    expect(screen.getByText(/I’m Abhishek’s AI career assistant/i)).toBeInTheDocument();
    expect(container.querySelector('.chat-message__badge')).toHaveAttribute('aria-hidden', 'true');
    expect(screen.getByText('Try asking:')).toBeInTheDocument();
    for (const question of suggestedQuestions) {
      expect(screen.getByRole('button', { name: question })).toBeInTheDocument();
    }
    expect(suggestedQuestions).toHaveLength(5);
  });

  it('renders the five questions in order as semantic one-per-row buttons', () => {
    mockFetchOnce(MOCK_RESPONSE);
    const { container } = render(<AssistantSection />);
    const list = container.querySelector('.chat-panel__suggestions-list') as HTMLElement;
    const items = Array.from(list.children);

    expect(items).toHaveLength(5);
    for (const [index, item] of items.entries()) {
      expect(item.tagName).toBe('LI');
      const button = item.querySelector('button') as HTMLButtonElement;
      expect(button).toHaveAttribute('type', 'button');
      expect(button).toHaveClass('suggested-question');
      expect(button).toHaveTextContent(suggestedQuestions[index]!);
    }
  });

  it('renders one conversation column with no permanent evidence panel', () => {
    mockFetchOnce(MOCK_RESPONSE);
    const { container } = render(<AssistantSection />);

    expect(container.querySelector('.evidence, .chat-panel__body')).toBeNull();
    expect(container.querySelectorAll('.chat-panel__transcript')).toHaveLength(1);
    expect(container.textContent).not.toMatch(
      /select a citation to inspect the supporting career evidence/i,
    );
    expect(container.textContent).not.toMatch(/^EVIDENCE$/m);
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
    expect(screen.queryByText('Try asking:')).not.toBeInTheDocument();
    expect(screen.getByText('Follow-up questions')).toBeInTheDocument();
    expect(screen.getByLabelText(/ask about abhishek’s experience/i)).toBeInTheDocument();
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

  it('opens the citation drawer on selection and labels the experience type', async () => {
    const user = userEvent.setup();
    mockFetchOnce(MOCK_RESPONSE);
    const { container } = render(<AssistantSection />);

    await user.click(screen.getByRole('button', { name: suggestedQuestions[0]! }));
    const citationButton = await screen.findByRole('button', { name: /^Source 1:/ });
    expect(container.querySelector('.badge--professional')).toHaveTextContent(
      'Professional Experience',
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    await user.click(citationButton);

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('A bounded approved excerpt.')).toBeInTheDocument();
    expect(within(dialog).getByText('Resume (placeholder)')).toBeInTheDocument();
  });

  it('labels portfolio citations as Portfolio Project without relying on color', async () => {
    const user = userEvent.setup();
    mockFetchOnce({
      ...MOCK_RESPONSE,
      citations: [
        {
          ...MOCK_RESPONSE.citations[0]!,
          source_type: 'PORTFOLIO_PROJECT',
          experience_type: 'PORTFOLIO',
        },
      ],
    });
    render(<AssistantSection />);

    await user.click(screen.getByRole('button', { name: suggestedQuestions[0]! }));

    expect(await screen.findByText('Portfolio Project')).toBeInTheDocument();
  });

  it('keeps a long citation excerpt inside the bounded drawer surface', async () => {
    const user = userEvent.setup();
    const longExcerpt = `Evidence${'Detail'.repeat(80)}`;
    mockFetchOnce({
      ...MOCK_RESPONSE,
      citations: [{ ...MOCK_RESPONSE.citations[0]!, excerpt: longExcerpt }],
    });
    const { container } = render(<AssistantSection />);

    await user.click(screen.getByRole('button', { name: suggestedQuestions[0]! }));
    await user.click(await screen.findByRole('button', { name: /^Source 1:/ }));

    expect(container.querySelector('.drawer__excerpt')).toHaveTextContent(longExcerpt);
  });

  it('keeps a long suggested question inside its full-width row', () => {
    mockFetchOnce(MOCK_RESPONSE);
    const { container } = render(<AssistantSection />);

    for (const button of container.querySelectorAll('.suggested-question')) {
      expect(button).toHaveClass('suggested-question');
      expect(button.parentElement?.tagName).toBe('LI');
    }
  });

  it('closes the citation drawer with Escape and returns focus to the trigger', async () => {
    const user = userEvent.setup();
    mockFetchOnce(MOCK_RESPONSE);
    render(<AssistantSection />);

    await user.click(screen.getByRole('button', { name: suggestedQuestions[0]! }));
    const citationButton = await screen.findByRole('button', { name: /^Source 1:/ });
    await user.click(citationButton);

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getAllByText('Professional Experience').length).toBeGreaterThan(0);

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
