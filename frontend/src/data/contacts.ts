import type { ContactMethod } from '../types/portfolio';

export interface ContactEnv {
  email?: string;
  linkedInUrl?: string;
  githubUrl?: string;
}

const EMAIL_PATTERN = /^[^\s@[\]]+@[^\s@[\]]+\.[^\s@[\]]+$/;

/**
 * Only configured public channels are ever exposed. Unconfigured, placeholder,
 * or unsafe values are omitted entirely rather than rendered as dead links.
 * Phone numbers, private email addresses, home addresses, and employer contact
 * details are out of scope.
 */
export function buildContactMethods(env: ContactEnv): ContactMethod[] {
  const methods: ContactMethod[] = [];

  const email = env.email?.trim();
  if (email && EMAIL_PATTERN.test(email)) {
    methods.push({
      id: 'contact-email',
      channel: 'email',
      badge: '@',
      label: 'Email',
      displayValue: email,
      url: `mailto:${email}`,
      external: false,
    });
  }

  const webChannels = [
    { channel: 'linkedin', label: 'LinkedIn', badge: 'in', value: env.linkedInUrl },
    { channel: 'github', label: 'GitHub', badge: '{ }', value: env.githubUrl },
  ] as const;

  for (const { channel, label, badge, value } of webChannels) {
    const url = toPublicWebUrl(value);
    if (!url) continue;
    methods.push({
      id: `contact-${channel}`,
      channel,
      badge,
      label,
      displayValue: displayHost(url),
      url,
      external: true,
    });
  }

  return methods;
}

/** Rejects placeholders and every scheme other than http(s). */
function toPublicWebUrl(value: string | undefined): string | null {
  const candidate = value?.trim();
  if (!candidate) return null;
  try {
    const parsed = new URL(candidate);
    return parsed.protocol === 'https:' || parsed.protocol === 'http:' ? parsed.toString() : null;
  } catch {
    return null;
  }
}

function displayHost(url: string): string {
  const parsed = new URL(url);
  return `${parsed.hostname}${parsed.pathname}`.replace(/\/$/, '');
}

/** Confirmed public profiles; env vars may override them per environment. */
const PUBLIC_PROFILES = {
  email: 'abhishekpalle1@gmail.com',
  linkedInUrl: 'https://www.linkedin.com/in/apalle1',
  githubUrl: 'https://github.com/apalle1',
};

export const contactMethods: ContactMethod[] = buildContactMethods({
  email: import.meta.env.VITE_PUBLIC_EMAIL || PUBLIC_PROFILES.email,
  linkedInUrl: import.meta.env.VITE_LINKEDIN_URL || PUBLIC_PROFILES.linkedInUrl,
  githubUrl: import.meta.env.VITE_GITHUB_URL || PUBLIC_PROFILES.githubUrl,
});
