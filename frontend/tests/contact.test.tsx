import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Footer } from '../src/sections/Footer';
import { buildContactMethods, contactMethods } from '../src/data/contacts';

describe('buildContactMethods', () => {
  it('creates methods only for configured channels', () => {
    const methods = buildContactMethods({ githubUrl: 'https://github.com/example' });

    expect(methods).toHaveLength(1);
    expect(methods[0]?.channel).toBe('github');
    expect(methods[0]?.url).toBe('https://github.com/example');
  });

  it('returns email, LinkedIn, and GitHub when all three are configured', () => {
    const methods = buildContactMethods({
      email: 'someone@example.com',
      linkedInUrl: 'https://www.linkedin.com/in/example',
      githubUrl: 'https://github.com/example',
    });

    expect(methods.map((m) => m.label)).toEqual(['Email', 'LinkedIn', 'GitHub']);
  });

  it('builds a mailto link for a configured public email', () => {
    const methods = buildContactMethods({ email: 'someone@example.com' });
    expect(methods[0]?.url).toBe('mailto:someone@example.com');
  });

  it('omits placeholder values instead of rendering them', () => {
    const methods = buildContactMethods({
      email: '[PUBLIC_EMAIL_TO_BE_PROVIDED]',
      linkedInUrl: '[LINKEDIN_URL_TO_BE_PROVIDED]',
      githubUrl: '[GITHUB_URL_TO_BE_PROVIDED]',
    });

    expect(methods).toHaveLength(0);
  });

  it('rejects unsafe URL schemes', () => {
    expect(buildContactMethods({ linkedInUrl: 'javascript:alert(1)' })).toHaveLength(0);
    expect(buildContactMethods({ githubUrl: 'data:text/html,<script>' })).toHaveLength(0);
  });

  it('returns nothing when no channel is configured', () => {
    expect(buildContactMethods({})).toHaveLength(0);
  });
});

describe('configured public profiles', () => {
  it('points email, LinkedIn, and GitHub at the confirmed public values', () => {
    expect(contactMethods.find((m) => m.channel === 'email')?.url).toBe(
      'mailto:abhishekpalle1@gmail.com',
    );
    expect(contactMethods.find((m) => m.channel === 'linkedin')?.url).toBe(
      'https://www.linkedin.com/in/apalle1',
    );
    expect(contactMethods.find((m) => m.channel === 'github')?.url).toBe(
      'https://github.com/apalle1',
    );
  });

  it('marks web profiles external and email internal', () => {
    for (const method of contactMethods) {
      expect(method.external).toBe(method.channel !== 'email');
    }
  });
});

describe('Footer', () => {
  it('renders the current year and the AI disclaimer in the dark forest footer', () => {
    const { container } = render(<Footer />);

    expect(screen.getByText(new RegExp(`${new Date().getFullYear()}`))).toBeInTheDocument();
    expect(screen.getByText(/may not capture every detail/i)).toBeInTheDocument();
    expect(container.querySelector('footer')).toHaveClass('footer');
  });

  it('renders every contact channel as an icon link with an accessible name', () => {
    const { container } = render(<Footer />);

    expect(container.querySelectorAll('.icon-link')).toHaveLength(contactMethods.length);
    for (const contact of contactMethods) {
      const link = screen.getByRole('link', { name: new RegExp(`^${contact.label}`) });
      expect(link).toHaveAttribute('href', contact.url);
      expect(link.textContent).toBe('');
      expect(link.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
    }
  });

  it('omits résumé and projects links', () => {
    const { container } = render(<Footer />);

    expect(screen.queryByRole('link', { name: /resume|cv|projects/i })).not.toBeInTheDocument();
    expect(container.querySelector('a[href$=".pdf"]')).toBeNull();
  });
});
