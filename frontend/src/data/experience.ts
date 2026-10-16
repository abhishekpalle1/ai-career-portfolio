import { isPublishableText } from './contentPolicy';
import type { ExperienceItem } from '../types/portfolio';

/**
 * Approved professional employment history, supplied and approved by Abhishek.
 *
 * Portfolio projects must never be added here — they belong in the assistant
 * knowledge base, where they are cited as PORTFOLIO_PROJECT sources.
 */
export const professionalExperience: ExperienceItem[] = [
  {
    id: 'cna-insurance',
    organization: 'CNA Insurance',
    startDate: 'March 2021',
    endDate: 'Present',
    isCurrent: true,
    role: 'Senior Machine Learning Engineer',
    summary:
      'Led AI/ML initiatives for commercial insurance, delivering production NLP and LLM applications and agentic workflows in the cloud.',
    sourceIds: ['approved-career-profile'],
    approved: true,
  },
  {
    id: 'stanley-black-decker',
    organization: 'Stanley Black & Decker',
    startDate: 'May 2019',
    endDate: 'December 2019',
    isCurrent: false,
    isInternship: true,
    role: 'Machine Learning Engineering',
    summary:
      'Developed ML solutions for demand forecasting and anomaly detection, improving operational planning and decision-making.',
    sourceIds: ['approved-career-profile'],
    approved: true,
  },
  {
    id: 'eternal-robotics',
    organization: 'Eternal Robotics',
    startDate: 'July 2017',
    endDate: 'June 2018',
    isCurrent: false,
    role: 'Machine Learning Engineer',
    summary:
      'Engineered and deployed an end-to-end computer vision system that transformed captured images into spatial guidance for the MYRO robot’s autonomous painting.',
    sourceIds: ['approved-career-profile'],
    approved: true,
  },
  {
    id: 'production-modeling-corporation',
    organization: 'Production Modeling Corporation',
    startDate: 'July 2016',
    endDate: 'June 2017',
    isCurrent: false,
    role: 'Senior Data Scientist',
    summary:
      'Delivered data-driven capacity planning and supply chain optimization solutions for Fortune 500 clients.',
    sourceIds: ['approved-career-profile'],
    approved: true,
  },
];

/** Only approved entries with complete, non-placeholder content may render. */
export function publishableExperience(items: ExperienceItem[]): ExperienceItem[] {
  return items.filter(
    (item) =>
      item.approved &&
      isPublishableText(item.organization) &&
      isPublishableText(item.role) &&
      isPublishableText(item.summary) &&
      isPublishableText(item.startDate) &&
      isPublishableText(item.endDate) &&
      (item.organizationQualifier === undefined || isPublishableText(item.organizationQualifier)),
  );
}
