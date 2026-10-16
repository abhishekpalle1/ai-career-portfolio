import type { Citation } from '../types/chat';

/** Shared so the panel, the list, and the drawer never drift apart. */
export const EXPERIENCE_TYPE_LABEL: Record<Citation['experience_type'], string> = {
  PROFESSIONAL: 'Professional Experience',
  PORTFOLIO: 'Portfolio Project',
  EDUCATION: 'Education',
  GENERAL: 'General',
};
