import { ChatPanel } from '../components/ChatPanel';
import { ErrorBoundary } from '../components/ErrorBoundary';

/** Frontend-only switch; never enabled in the production environment. */
const showMockNotice = import.meta.env.VITE_SHOW_MOCK_NOTICE === 'true';

export function AssistantSection() {
  return (
    <section id="assistant" className="section assistant" aria-labelledby="assistant-title">
      <div className="container assistant__inner">
        <h2 id="assistant-title" className="assistant__heading">
          Ask My AI
        </h2>
        <p className="assistant__description">
          Get instant answers about my experience, projects, and more.
        </p>
        {showMockNotice ? (
          <p className="assistant__mock-notice">Mock responses — live RAG integration pending</p>
        ) : null}

        <ErrorBoundary
          fallback={
            <p className="chat-panel__error" role="alert">
              The AI assistant is temporarily unavailable. You can still explore Abhishek’s
              experience and contact details on this page.
            </p>
          }
        >
          <ChatPanel />
        </ErrorBoundary>
      </div>
    </section>
  );
}
