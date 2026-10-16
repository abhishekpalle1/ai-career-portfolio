export type WorkType = 'professional' | 'portfolio';

export interface Profile {
  fullName: string;
  initials: string;
  professionalTitle: string;
  valueProposition: string;
  /** Set to `null` until an availability statement has been approved. */
  availabilityStatement: string | null;
  photoUrl: string | null;
  photoAlt: string;
}

export interface CareerMetric {
  id: string;
  value: string;
  label: string;
  sourceId?: string;
}

export interface FeaturedWork {
  id: string;
  type: WorkType;
  organization: string;
  dateRange: string;
  title: string;
  role: string;
  description: string;
  impact?: string;
  technologies: string[];
  publicUrl?: string;
  sourceIds: string[];
}

export type ContactChannel = 'email' | 'linkedin' | 'github' | 'calendar';

export interface ContactMethod {
  id: string;
  channel: ContactChannel;
  badge: string;
  category: string;
  /** Public display value, or a clearly marked placeholder. */
  displayValue: string;
  /** Omitted until a public URL has been configured. */
  url?: string;
  external: boolean;
}
