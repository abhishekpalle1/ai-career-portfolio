import type { ContactMethod } from '../types/portfolio';

export interface ContactEnv {
  email?: string;
  linkedInUrl?: string;
  githubUrl?: string;
}

/**
 * Only public contact channels are ever exposed. Phone numbers, private email
 * addresses, home addresses, and employer contact details are out of scope.
 *
 * Channels without a configured value render as a clearly marked placeholder
 * rather than a broken link.
 */
export function buildContactMethods(env: ContactEnv): ContactMethod[] {
  const email = env.email?.trim();
  const linkedInUrl = env.linkedInUrl?.trim();
  const githubUrl = env.githubUrl?.trim();

  return [
    {
      id: 'contact-email',
      channel: 'email',
      badge: '@',
      category: 'Email',
      displayValue: email ?? '[PUBLIC_EMAIL_TO_BE_PROVIDED]',
      ...(email ? { url: `mailto:${email}` } : {}),
      external: false,
    },
    {
      id: 'contact-linkedin',
      channel: 'linkedin',
      badge: 'in',
      category: 'LinkedIn',
      displayValue: linkedInUrl ? displayHost(linkedInUrl) : '[LINKEDIN_URL_TO_BE_PROVIDED]',
      ...(linkedInUrl ? { url: linkedInUrl } : {}),
      external: true,
    },
    {
      id: 'contact-github',
      channel: 'github',
      badge: '{ }',
      category: 'GitHub',
      displayValue: githubUrl ? displayHost(githubUrl) : '[GITHUB_URL_TO_BE_PROVIDED]',
      ...(githubUrl ? { url: githubUrl } : {}),
      external: true,
    },
  ];
}

function displayHost(url: string): string {
  try {
    const parsed = new URL(url);
    return `${parsed.hostname}${parsed.pathname}`.replace(/\/$/, '');
  } catch {
    return url;
  }
}

export const contactMethods: ContactMethod[] = buildContactMethods({
  email: import.meta.env.VITE_PUBLIC_EMAIL,
  linkedInUrl: import.meta.env.VITE_LINKEDIN_URL,
  githubUrl: import.meta.env.VITE_GITHUB_URL,
});
