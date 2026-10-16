import type { ContactMethod } from '../types/portfolio';

interface ContactCardProps {
  contact: ContactMethod;
}

export function ContactCard({ contact }: ContactCardProps) {
  return (
    <div className="contact-card">
      <span className="contact-card__badge" aria-hidden="true">
        {contact.badge}
      </span>
      <span className="contact-card__category">{contact.category}</span>
      {contact.url ? (
        <a
          className="contact-card__value"
          href={contact.url}
          {...(contact.external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
        >
          {contact.displayValue}
          {contact.external ? <span className="visually-hidden"> (opens in a new tab)</span> : null}
        </a>
      ) : (
        <span className="contact-card__value contact-card__value--placeholder">
          {contact.displayValue}
        </span>
      )}
    </div>
  );
}
