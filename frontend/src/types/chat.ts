export type ExperienceType = 'PROFESSIONAL' | 'PORTFOLIO' | 'EDUCATION' | 'GENERAL';

export type SourceType =
  | 'RESUME'
  | 'PROFESSIONAL_PROFILE'
  | 'PROFESSIONAL_EXPERIENCE'
  | 'PORTFOLIO_PROJECT'
  | 'SKILLS_EVIDENCE'
  | 'EDUCATION'
  | 'CERTIFICATION'
  | 'RECRUITER_FAQ'
  | 'PUBLIC_CONTACT';

export interface Citation {
  citation_id: string;
  chunk_id: string;
  source_name: string;
  source_type: SourceType;
  section: string;
  experience_type: ExperienceType;
  source_url: string;
  excerpt: string;
}

export interface ChatRequestPayload {
  message: string;
  session_id?: string;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  suggested_questions: string[];
  intent: string;
  grounded: boolean;
  abstained: boolean;
  trace_id: string;
}

export type ChatRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  text: string;
  abstained: boolean;
}

export type AssistantStatus = 'idle' | 'loading' | 'error';

export type ApiErrorKind = 'unavailable' | 'invalid' | 'unexpected';

export class ApiError extends Error {
  readonly kind: ApiErrorKind;

  constructor(kind: ApiErrorKind, message: string) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
  }
}
