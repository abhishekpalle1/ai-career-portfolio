import { ContactIcon } from '../components/ContactIcon';
import { HeroProofPoint } from '../components/HeroProofPoint';
import { contactMethods } from '../data/contacts';
import { heroProofPoints, publishableProofPoints } from '../data/heroProofPoints';
import { profile } from '../data/profile';

export function HeroSection() {
  const proofPoints = publishableProofPoints(heroProofPoints);
  const descriptionRest = profile.valueProposition.slice(profile.valuePropositionEmphasis.length);

  return (
    <section id="home" className="hero" aria-labelledby="hero-name">
      <div className="container hero__inner">
        {proofPoints.length > 0 ? (
          <ul className="hero__proof-points" aria-label="Career proof points">
            {proofPoints.map((proofPoint) => (
              <HeroProofPoint key={proofPoint.id} proofPoint={proofPoint} />
            ))}
          </ul>
        ) : null}

        <p className="hero__greeting">{profile.greeting}</p>
        <h1 id="hero-name" className="hero__name">
          {profile.fullName}
        </h1>
        <p className="hero__description">
          <strong>{profile.valuePropositionEmphasis}</strong>
          {descriptionRest}
        </p>

        <div className="hero__actions">
          <a className="button button--accent" href="#experience">
            Explore Experience
          </a>
          <a className="button button--primary" href="#assistant">
            Chat with My AI
            <span aria-hidden="true"> ↓</span>
          </a>
        </div>

        {contactMethods.length > 0 ? (
          <ul className="hero__links" aria-label="Public profile links">
            {contactMethods.map((contact) => (
              <li key={contact.id}>
                <a
                  className="icon-link"
                  href={contact.url}
                  aria-label={
                    contact.external ? `${contact.label} (opens in a new tab)` : contact.label
                  }
                  {...(contact.external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
                >
                  <ContactIcon channel={contact.channel} />
                </a>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </section>
  );
}
