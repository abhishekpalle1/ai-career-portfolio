interface SectionHeadingProps {
  id?: string;
  title: string;
  description?: string;
  variant?: 'default' | 'inverse';
}

export function SectionHeading({
  id,
  title,
  description,
  variant = 'default',
}: SectionHeadingProps) {
  return (
    <header className={`section-heading section-heading--${variant}`}>
      <h2 id={id} className="section-heading__title">
        {title}
      </h2>
      {description ? <p className="section-heading__description">{description}</p> : null}
    </header>
  );
}
