export interface Profile {
  fullName: string;
  greeting: string;
  valueProposition: string;
  valuePropositionEmphasis: string;
}

/**
 * A compact hero credibility statement. Numeric values are published only when
 * they are verified, approved, and traceable to at least one source ID.
 */
export interface HeroProofPoint {
  id: string;
  value?: string;
  label: string;
  description?: string;
  verified: boolean;
  approved: boolean;
  sourceIds: string[];
}

/** Approved professional employment only. Portfolio projects never belong here. */
export interface ExperienceItem {
  id: string;
  organization: string;
  organizationQualifier?: string;
  startDate: string;
  endDate: string;
  isCurrent: boolean;
  isInternship?: boolean;
  role: string;
  summary: string;
  sourceIds: string[];
  approved: boolean;
}

export type ContactChannel = 'email' | 'linkedin' | 'github';

export interface ContactMethod {
  id: string;
  channel: ContactChannel;
  badge: string;
  label: string;
  displayValue: string;
  url: string;
  external: boolean;
}
