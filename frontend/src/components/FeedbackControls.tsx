import { useState } from 'react';

interface FeedbackControlsProps {
  messageId: string;
}

type Choice = 'helpful' | 'not-helpful';

/** Phase 1 records feedback locally only; no feedback endpoint is called yet. */
export function FeedbackControls({ messageId }: FeedbackControlsProps) {
  const [choice, setChoice] = useState<Choice | null>(null);

  if (choice) {
    return (
      <p className="feedback feedback--submitted" role="status">
        Thanks for the feedback.
      </p>
    );
  }

  return (
    <div className="feedback" role="group" aria-label="Was this answer helpful?">
      <span className="feedback__prompt">Was this helpful?</span>
      <button
        type="button"
        className="feedback__button"
        onClick={() => setChoice('helpful')}
        aria-label={`Mark answer ${messageId} as helpful`}
      >
        Helpful
      </button>
      <button
        type="button"
        className="feedback__button"
        onClick={() => setChoice('not-helpful')}
        aria-label={`Mark answer ${messageId} as not helpful`}
      >
        Not helpful
      </button>
    </div>
  );
}
