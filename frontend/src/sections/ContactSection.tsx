import { ContactCard } from '../components/ContactCard';
import { SectionHeading } from '../components/SectionHeading';
import { contactMethods } from '../data/contacts';
import { profile } from '../data/profile';

export function ContactSection() {
  return (
    <section id="contact" className="section contact" aria-labelledby="contact-title">
      <div className="container contact__inner">
        {profile.availabilityStatement ? (
          <p className="contact__availability">
            <span className="contact__availability-dot" aria-hidden="true" />
            {profile.availabilityStatement}
          </p>
        ) : null}

        <SectionHeading
          id="contact-title"
          title="Let’s Connect"
          description="I’m open to discussing ML/AI roles, production AI systems, and relevant collaboration opportunities."
        />

        <div className="contact__grid">
          {contactMethods.slice(0, 3).map((contact) => (
            <ContactCard key={contact.id} contact={contact} />
          ))}
        </div>
      </div>
    </section>
  );
}
