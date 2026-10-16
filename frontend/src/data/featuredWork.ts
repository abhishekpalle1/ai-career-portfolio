import type { FeaturedWork } from '../types/portfolio';

/**
 * Featured work.
 *
 * Entries 1 and 2 are placeholders awaiting approved professional content.
 * Entry 3 describes this portfolio project and is labelled `portfolio` so it is
 * never presented as employer work.
 */
export const featuredWork: FeaturedWork[] = [
  {
    id: 'work-professional-1',
    type: 'professional',
    organization: '[EMPLOYER_1_NAME_TO_BE_PROVIDED]',
    dateRange: '[DATE_RANGE_TO_BE_PROVIDED]',
    title: '[PRODUCTION_AI_SYSTEM_TITLE_TO_BE_PROVIDED]',
    role: '[ROLE_TO_BE_PROVIDED]',
    description:
      '[DESCRIPTION_TO_BE_PROVIDED] Two to four sentences describing the production AI or LLM system, the problem it solved, and the approach taken. No claim should appear here unless it is supported by approved source material.',
    technologies: ['[TECH_1]', '[TECH_2]', '[TECH_3]'],
    sourceIds: [],
  },
  {
    id: 'work-professional-2',
    type: 'professional',
    organization: '[EMPLOYER_2_NAME_TO_BE_PROVIDED]',
    dateRange: '[DATE_RANGE_TO_BE_PROVIDED]',
    title: '[PRODUCTION_ML_OR_EVALUATION_SYSTEM_TITLE_TO_BE_PROVIDED]',
    role: '[ROLE_TO_BE_PROVIDED]',
    description:
      '[DESCRIPTION_TO_BE_PROVIDED] Two to four sentences describing the production ML or model-evaluation system, the modelling approach, and how results were validated.',
    technologies: ['[TECH_1]', '[TECH_2]', '[TECH_3]'],
    sourceIds: [],
  },
  {
    id: 'work-portfolio-1',
    type: 'portfolio',
    organization: 'Personal portfolio project',
    dateRange: 'In progress',
    title: 'AI Career Portfolio and Resume RAG Assistant',
    role: 'Solo design and implementation',
    description:
      'A recruiter-facing portfolio site with a retrieval-augmented career assistant. A React and TypeScript single-page frontend calls a FastAPI backend that answers questions strictly from approved career documents. The system is being built incrementally: the current phase covers the frontend, the API contract, and deterministic mock responses.',
    impact: 'Not yet deployed. No production usage or performance claims are made.',
    technologies: ['React', 'TypeScript', 'Vite', 'FastAPI', 'Python', 'Pytest', 'Vitest'],
    publicUrl: import.meta.env.VITE_GITHUB_URL || undefined,
    sourceIds: [],
  },
];
