import type { Profile } from '../types/portfolio';

/**
 * Editable profile content.
 *
 * PLACEHOLDER POLICY: values wrapped in square brackets have not been
 * verified and must be replaced (or set to `null`) before production.
 */
export const profile: Profile = {
  fullName: 'Abhishek Palle',
  greeting: 'Hello, it’s',
  valueProposition:
    'AI & ML Engineer building production-grade pipelines, ML systems, LLM applications, and data-driven analytics.',
  /** Leading phrase of `valueProposition` rendered with emphasis. */
  valuePropositionEmphasis: 'AI & ML Engineer',
};
