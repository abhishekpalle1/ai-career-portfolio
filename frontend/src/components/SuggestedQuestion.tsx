interface SuggestedQuestionProps {
  question: string;
  disabled: boolean;
  onSelect: (question: string) => void;
}

export function SuggestedQuestion({ question, disabled, onSelect }: SuggestedQuestionProps) {
  return (
    <li>
      <button
        type="button"
        className="suggested-question"
        disabled={disabled}
        onClick={() => onSelect(question)}
      >
        <span className="suggested-question__text">{question}</span>
        <span className="suggested-question__arrow" aria-hidden="true">
          →
        </span>
      </button>
    </li>
  );
}
