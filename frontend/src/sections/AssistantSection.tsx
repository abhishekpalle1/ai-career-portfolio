import { ChatPanel } from '../components/ChatPanel';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { SectionHeading } from '../components/SectionHeading';

export function AssistantSection() {
  return (
    <section id="assistant" className="section assistant" aria-labelledby="assistant-title">
      <div className="container">
        <SectionHeading
          id="assistant-title"
          title="Ask My AI"
          description="Get instant answers about my experience, projects, and skills."
        />
        <ErrorBoundary
          fallback={
            <p className="chat-panel__error" role="alert">
              The AI assistant is temporarily unavailable. You can still explore Abhishek’s
              experience, projects, skills, and resume on this page.
            </p>
          }
        >
          <ChatPanel />
        </ErrorBoundary>
      </div>
    </section>
  );
}
