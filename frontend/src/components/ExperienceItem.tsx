import type { ExperienceItem as ExperienceItemModel } from '../types/portfolio';

interface ExperienceItemProps {
  item: ExperienceItemModel;
}

export function ExperienceItem({ item }: ExperienceItemProps) {
  const roleId = `${item.id}-role`;

  return (
    <li className="experience-item">
      <div className="experience-item__header">
        <p className="experience-item__organization">
          {item.organization}
          {item.organizationQualifier ? (
            <span className="experience-item__qualifier">({item.organizationQualifier})</span>
          ) : null}
          {item.isCurrent ? <span className="badge badge--current">CURRENT</span> : null}
          {item.isInternship ? <span className="badge badge--internship">INTERNSHIP</span> : null}
        </p>

        <p className="experience-item__dates">
          {item.startDate} – {item.endDate}
        </p>
      </div>

      <h3 id={roleId} className="experience-item__role">
        {item.role}
      </h3>
      <p className="experience-item__summary">{item.summary}</p>
    </li>
  );
}
