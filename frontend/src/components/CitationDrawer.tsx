import { useEffect, useRef } from 'react';
import type { Citation } from '../types/chat';

interface CitationDrawerProps {
  citation: Citation | null;
  onClose: () => void;
}

export function CitationDrawer({ citation, onClose }: CitationDrawerProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!citation) return;

    previouslyFocusedRef.current = document.activeElement as HTMLElement | null;
    closeButtonRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.stopPropagation();
        onClose();
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previouslyFocusedRef.current?.focus();
    };
  }, [citation, onClose]);

  if (!citation) return null;

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="citation-drawer-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="drawer__header">
          <h3 id="citation-drawer-title" className="drawer__title">
            {citation.source_name}
          </h3>
          <button
            ref={closeButtonRef}
            type="button"
            className="drawer__close"
            onClick={onClose}
            aria-label="Close source details"
          >
            ×
          </button>
        </div>

        <dl className="drawer__meta">
          <div>
            <dt>Section</dt>
            <dd>{citation.section}</dd>
          </div>
          <div>
            <dt>Source type</dt>
            <dd>{citation.source_type.replaceAll('_', ' ').toLowerCase()}</dd>
          </div>
          <div>
            <dt>Experience type</dt>
            <dd>{citation.experience_type.toLowerCase()}</dd>
          </div>
        </dl>

        <blockquote className="drawer__excerpt">{citation.excerpt}</blockquote>

        {citation.source_url ? (
          <a
            className="drawer__link"
            href={citation.source_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open full source
            <span className="visually-hidden"> (opens in a new tab)</span>
          </a>
        ) : null}
      </aside>
    </div>
  );
}
