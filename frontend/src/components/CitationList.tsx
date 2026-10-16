import type { Citation } from '../types/chat';

interface CitationListProps {
  citations: Citation[];
  onSelect: (citation: Citation) => void;
}

const EXPERIENCE_LABEL: Record<Citation['experience_type'], string> = {
  PROFESSIONAL: 'Professional',
  PORTFOLIO: 'Portfolio',
  EDUCATION: 'Education',
  GENERAL: 'General',
};

export function CitationList({ citations, onSelect }: CitationListProps) {
  if (citations.length === 0) return null;

  return (
    <div className="citations">
      <h4 className="citations__title">Sources</h4>
      <ol className="citations__list">
        {citations.map((citation, index) => (
          <li key={citation.citation_id} className="citations__item">
            <button
              type="button"
              className="citations__button"
              onClick={() => onSelect(citation)}
              aria-label={`Source ${index + 1}: ${citation.source_name}, ${citation.section}. Open source details.`}
            >
              <span className="citations__marker">[{index + 1}]</span>
              <span className="citations__name">{citation.source_name}</span>
              <span className="citations__section">{citation.section}</span>
            </button>
            <span className={`badge badge--${citation.experience_type.toLowerCase()}`}>
              {EXPERIENCE_LABEL[citation.experience_type]}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
