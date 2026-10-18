import { FeedbackControls } from './FeedbackControls';
import type { ChatMessage as ChatMessageModel } from '../types/chat';

// Citations stay internal to the backend; markers such as [C1] or [C1, C3] are never shown.
const CITATION_MARKER = /[ \t]*\[\s*C\d+(?:\s*,\s*C\d+)*\s*\]/g;

interface ChatMessageProps {
  message: ChatMessageModel;
  showFeedback: boolean;
}

export function ChatMessage({ message, showFeedback }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const roleLabel = isUser ? 'You asked' : 'Assistant answered';
  const text = isUser ? message.text : message.text.replace(CITATION_MARKER, '');

  return (
    <div className={`chat-message chat-message--${message.role}`}>
      <span className="visually-hidden">{roleLabel}:</span>
      {!isUser ? (
        <span className="chat-message__badge" aria-hidden="true">
          AI
        </span>
      ) : null}
      <div className="chat-message__bubble">
        {/* Rendered as plain text. Model output is never injected as HTML. */}
        {text.split('\n').map((line, index) =>
          line.trim().startsWith('- ') ? (
            <span key={index} className="chat-message__bullet">
              {line.trim().slice(2)}
            </span>
          ) : (
            <p key={index} className="chat-message__line">
              {line}
            </p>
          ),
        )}

        {message.abstained ? (
          <p className="chat-message__notice">
            Not enough approved evidence was available to answer this question.
          </p>
        ) : null}

        {showFeedback ? <FeedbackControls messageId={message.id} /> : null}
      </div>
    </div>
  );
}
