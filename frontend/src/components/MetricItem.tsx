import type { CareerMetric } from '../types/portfolio';

interface MetricItemProps {
  metric: CareerMetric;
}

export function MetricItem({ metric }: MetricItemProps) {
  return (
    <div className="metric">
      <span className="metric__value">{metric.value}</span>
      <span className="metric__label">{metric.label}</span>
    </div>
  );
}
