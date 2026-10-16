import { SectionHeading } from '../components/SectionHeading';
import { WorkCard } from '../components/WorkCard';
import { featuredWork } from '../data/featuredWork';

export function FeaturedWorkSection() {
  return (
    <section id="work" className="section featured-work" aria-labelledby="featured-work-title">
      <div className="container">
        <SectionHeading
          id="featured-work-title"
          title="Featured Work"
          description="Selected systems and projects with measurable impact."
        />
        <div className="featured-work__grid">
          {featuredWork.slice(0, 3).map((work) => (
            <WorkCard key={work.id} work={work} />
          ))}
        </div>
      </div>
    </section>
  );
}
