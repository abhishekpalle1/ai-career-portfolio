import type { Profile } from '../types/portfolio';

/**
 * Editable profile content.
 *
 * PLACEHOLDER POLICY: values wrapped in square brackets have not been
 * verified and must be replaced (or set to `null`) before production.
 */
export const profile: Profile = {
  fullName: 'Abhishek Palle',
  initials: 'AP',
  professionalTitle: 'Senior Data Scientist | ML/AI Engineer',
  valueProposition:
    'I build production AI and machine-learning systems spanning LLM applications, evaluation, intelligent workflows, and cloud deployment.',
  // Confirm or set to `null` before publishing.
  availabilityStatement: 'Open to relevant ML/AI opportunities',
  // No likeness is generated. Supply a real photo URL or keep `null` to show initials.
  photoUrl: null,
  photoAlt: 'Professional headshot of Abhishek Palle',
};

export const resumeUrl: string = import.meta.env.VITE_RESUME_URL ?? '/resume.pdf';
