import { Button } from '../components/Button';
import { profile } from '../data/profile';

function scrollToSection(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

export function HeroSection() {
  return (
    <section id="home" className="hero" aria-labelledby="hero-name">
      <div className="container hero__inner">
        <div className="hero__avatar">
          {profile.photoUrl ? (
            <img src={profile.photoUrl} alt={profile.photoAlt} className="hero__photo" />
          ) : (
            <span className="hero__initials" aria-hidden="true">
              {profile.initials}
            </span>
          )}
          {profile.availabilityStatement ? (
            <span className="hero__availability-dot" aria-hidden="true" />
          ) : null}
        </div>

        {profile.availabilityStatement ? (
          <p className="hero__availability">{profile.availabilityStatement}</p>
        ) : null}

        <h1 id="hero-name" className="hero__name">
          {profile.fullName}
        </h1>
        <p className="hero__title">{profile.professionalTitle}</p>
        <p className="hero__value-proposition">{profile.valueProposition}</p>

        <div className="hero__actions">
          <Button onClick={() => scrollToSection('assistant')}>Chat with My AI ↓</Button>
          <Button variant="secondary" onClick={() => scrollToSection('contact')}>
            Get in Touch
          </Button>
        </div>
      </div>
    </section>
  );
}
