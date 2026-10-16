import { isPublishableText } from './contentPolicy';
import type { HeroProofPoint } from '../types/portfolio';

/**
 * Hero proof points.
 *
 * Both values are supplied as verified and approved career-profile facts and
 * retain a source ID for later RAG citation. Unverified, unapproved, or
 * unsourced numeric claims are filtered out before render.
 */
export const heroProofPoints: HeroProofPoint[] = [
  {
    id: 'engineering-experience',
    value: '8+ yrs',
    label: 'Engineering Experience',
    verified: true,
    approved: true,
    sourceIds: ['approved-career-profile'],
  },
  {
    id: 'projects-delivered',
    value: '15+',
    label: 'Projects Delivered',
    verified: true,
    approved: true,
    sourceIds: ['approved-career-profile'],
  },
];

const MAX_PROOF_POINTS = 2;

/** Numeric claims additionally require a retained source ID. */
export function publishableProofPoints(points: HeroProofPoint[]): HeroProofPoint[] {
  return points
    .filter((point) => {
      if (!point.verified || !point.approved) return false;
      if (!isPublishableText(point.label)) return false;
      if (point.description !== undefined && !isPublishableText(point.description)) return false;
      if (point.value === undefined) return true;
      return isPublishableText(point.value) && point.sourceIds.length > 0;
    })
    .slice(0, MAX_PROOF_POINTS);
}
