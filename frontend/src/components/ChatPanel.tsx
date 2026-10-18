import { useEffect, useRef, useState } from 'react';
import { ChatMessage } from './ChatMessage';
import { SuggestedQuestion } from './SuggestedQuestion';
import { MAX_INPUT_CHARACTERS } from '../api/careerAssistantApi';
import { useCareerAssistant } from '../hooks/useCareerAssistant';
import { suggestedQuestions } from '../data/suggestedQuestions';

const COUNTER_VISIBLE_FROM = MAX_INPUT_CHARACTERS - 100;

export function ChatPanel() {
  const { messages, status, errorMessage, followUpQuestions, showSuggestions, askQuestion } =
    useCareerAssistant();
  const [draft, setDraft] = useState('');
  const transcriptRef = useRef<HTMLDivElement>(null);

  const isLoading = status === 'loading';
  const lastMessage = messages[messages.length - 1];

  useEffect(() => {
    const transcript = transcriptRef.current;
    if (transcript) {
      transcript.scrollTop = transcript.scrollHeight;
    }
  }, [messages.length, status]);

  async function submit(question: string) {
    setDraft('');
    await askQuestion(question);
  }

  return (
    <div className="chat-panel">
      <div className="chat-panel__header">
        <span className="chat-panel__dots" aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
        <strong className="chat-panel__title">AI Career Assistant</strong>
        <span className="chat-panel__grounding">Grounded in approved career materials</span>
      </div>

      <div
        ref={transcriptRef}
        className="chat-panel__transcript"
        role="log"
        aria-live="polite"
        aria-label="Conversation with the AI career assistant"
      >
        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            message={message}
            showFeedback={
              message.role === 'assistant' &&
              message.id !== 'assistant-welcome' &&
              message.id === lastMessage?.id
            }
          />
        ))}

        {isLoading ? (
          <p className="chat-panel__loading" role="status">
            <span className="chat-panel__spinner" aria-hidden="true" />
            Searching approved career materials…
          </p>
        ) : null}

        {errorMessage ? (
          <p className="chat-panel__error" role="alert">
            {errorMessage}
          </p>
        ) : null}

        {showSuggestions ? (
          <div className="chat-panel__suggestions">
            <p className="chat-panel__suggestions-title" id="suggested-questions-label">
              Try asking:
            </p>
            <ul
              className="chat-panel__suggestions-list"
              aria-labelledby="suggested-questions-label"
            >
              {suggestedQuestions.map((question) => (
                <SuggestedQuestion
                  key={question}
                  question={question}
                  disabled={isLoading}
                  onSelect={submit}
                />
              ))}
            </ul>
          </div>
        ) : null}

        {!showSuggestions && followUpQuestions.length > 0 && !isLoading ? (
          <div className="chat-panel__suggestions">
            <p className="chat-panel__suggestions-title" id="follow-up-questions-label">
              Follow-up questions
            </p>
            <ul
              className="chat-panel__suggestions-list"
              aria-labelledby="follow-up-questions-label"
            >
              {followUpQuestions.map((question) => (
                <SuggestedQuestion
                  key={question}
                  question={question}
                  disabled={isLoading}
                  onSelect={submit}
                />
              ))}
            </ul>
          </div>
        ) : null}
      </div>

      <div className="chat-panel__footer">
        <form
          className="chat-panel__form"
          onSubmit={(event) => {
            event.preventDefault();
            void submit(draft);
          }}
        >
          <label className="visually-hidden" htmlFor="assistant-input">
            Ask about Abhishek’s experience
          </label>
          <input
            id="assistant-input"
            className="chat-panel__input"
            type="text"
            value={draft}
            maxLength={MAX_INPUT_CHARACTERS}
            placeholder="Ask about Abhishek’s experience..."
            autoComplete="off"
            disabled={isLoading}
            onChange={(event) => setDraft(event.target.value)}
            aria-describedby="assistant-input-help"
          />
          <button
            type="submit"
            className="chat-panel__submit"
            disabled={isLoading || draft.trim().length === 0}
            aria-label="Send question"
          >
            <span aria-hidden="true">→</span>
          </button>
        </form>

        <p id="assistant-input-help" className="chat-panel__help">
          {draft.length >= COUNTER_VISIBLE_FROM
            ? `${draft.length} of ${MAX_INPUT_CHARACTERS} characters`
            : 'Press Enter to send. Answers are grounded in approved career materials.'}
        </p>
      </div>
    </div>
  );
}
