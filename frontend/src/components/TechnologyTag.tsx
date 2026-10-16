interface TechnologyTagProps {
  label: string;
}

export function TechnologyTag({ label }: TechnologyTagProps) {
  return <li className="tech-tag">{label}</li>;
}
