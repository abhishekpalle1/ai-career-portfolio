import { CitationList } from './CitationList';
import { FeedbackControls } from './FeedbackControls';
import type { ChatMessage as ChatMessageModel, Citation } from '../types/chat';

interface ChatMessageProps {
  message: ChatMessageModel;
  onSelectCitation: (citation: Citation) => void;
  showFeedback: boolean;
}

export function ChatMessage({ message, onSelectCitation, showFeedback }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const roleLabel = isUser ? 'You asked' : 'Assistant answered';

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
        {message.text.split('\n').map((line, index) =>
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

        {!isUser ? (
          <CitationList citations={message.citations} onSelect={onSelectCitation} />
        ) : null}

        {showFeedback ? <FeedbackControls messageId={message.id} /> : null}
      </div>
    </div>
  );
}
