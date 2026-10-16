import { TechnologyTag } from './TechnologyTag';
import type { FeaturedWork } from '../types/portfolio';

interface WorkCardProps {
  work: FeaturedWork;
}

const TYPE_LABEL: Record<FeaturedWork['type'], string> = {
  professional: 'Professional',
  portfolio: 'Portfolio project',
};

export function WorkCard({ work }: WorkCardProps) {
  const headingId = `${work.id}-title`;

  return (
    <article className="work-card" aria-labelledby={headingId}>
      <div className="work-card__meta">
        <span className="work-card__organization">{work.organization}</span>
        <span className="work-card__dates">{work.dateRange}</span>
      </div>

      <h3 id={headingId} className="work-card__title">
        {work.title}
      </h3>
      <p className="work-card__role">{work.role}</p>

      <span className={`badge badge--${work.type}`}>{TYPE_LABEL[work.type]}</span>

      <p className="work-card__description">{work.description}</p>

      {work.impact ? (
        <p className="work-card__impact">
          <span className="work-card__impact-label">Outcome: </span>
          {work.impact}
        </p>
      ) : null}

      <ul className="work-card__technologies" aria-label={`Technologies used in ${work.title}`}>
        {work.technologies.map((technology) => (
          <TechnologyTag key={technology} label={technology} />
        ))}
      </ul>

      {work.publicUrl ? (
        <a
          className="work-card__link"
          href={work.publicUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          View project
          <span className="visually-hidden"> {work.title} (opens in a new tab)</span>
        </a>
      ) : null}
    </article>
  );
}
