import { ExperienceItem } from '../components/ExperienceItem';
import { professionalExperience, publishableExperience } from '../data/experience';

export function ExperienceSection() {
  const items = publishableExperience(professionalExperience);

  return (
    <section id="experience" className="section section--alt" aria-labelledby="experience-title">
      <div className="container experience__layout">
        <h2 id="experience-title" className="experience__heading">
          Experience
        </h2>

        {items.length > 0 ? (
          <ol className="experience__list" aria-label="Professional experience">
            {items.map((item) => (
              <ExperienceItem key={item.id} item={item} />
            ))}
          </ol>
        ) : null}
      </div>
    </section>
  );
}
