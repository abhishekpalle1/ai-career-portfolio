import { profile, resumeUrl } from '../data/profile';
import { contactMethods } from '../data/contacts';

export function Footer() {
  const year = new Date().getFullYear();
  const linkable = contactMethods.filter((contact) => Boolean(contact.url) && contact.external);

  return (
    <footer className="footer">
      <div className="container footer__inner">
        <p className="footer__copyright">
          © {year} {profile.fullName}
        </p>

        <nav className="footer__links" aria-label="Footer links">
          <a href={resumeUrl} target="_blank" rel="noopener noreferrer">
            Resume
            <span className="visually-hidden"> (opens in a new tab)</span>
          </a>
          {linkable.map((contact) => (
            <a key={contact.id} href={contact.url} target="_blank" rel="noopener noreferrer">
              {contact.category}
              <span className="visually-hidden"> (opens in a new tab)</span>
            </a>
          ))}
        </nav>

        <p className="footer__disclaimer">
          AI-generated answers are based on approved career materials and may not capture every
          detail.
        </p>
      </div>
    </footer>
  );
}
