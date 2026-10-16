import { MetricItem } from '../components/MetricItem';
import { careerMetrics } from '../data/metrics';

export function MetricsSection() {
  if (careerMetrics.length === 0) return null;

  return (
    <section className="metrics" aria-label="Career metrics">
      <div className="container metrics__inner">
        {careerMetrics.slice(0, 4).map((metric) => (
          <MetricItem key={metric.id} metric={metric} />
        ))}
      </div>
    </section>
  );
}
