import { ContactIcon } from '../components/ContactIcon';
import { contactMethods } from '../data/contacts';
import { profile } from '../data/profile';

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="footer">
      <div className="container footer__inner">
        <nav className="footer__links" aria-label="Footer links">
          {contactMethods.map((contact) => (
            <a
              key={contact.id}
              className="icon-link icon-link--inverse"
              href={contact.url}
              aria-label={
                contact.external ? `${contact.label} (opens in a new tab)` : contact.label
              }
              {...(contact.external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
            >
              <ContactIcon channel={contact.channel} />
            </a>
          ))}
        </nav>

        <p className="footer__copyright">
          © {year} {profile.fullName}
        </p>

        <p className="footer__disclaimer">
          AI-generated answers are based on approved career materials and may not capture every
          detail.
        </p>
      </div>
    </footer>
  );
}
