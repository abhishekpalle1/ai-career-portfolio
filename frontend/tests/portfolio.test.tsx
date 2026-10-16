import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FeaturedWorkSection } from '../src/sections/FeaturedWorkSection';
import { ContactSection } from '../src/sections/ContactSection';
import { Footer } from '../src/sections/Footer';
import { featuredWork } from '../src/data/featuredWork';
import { buildContactMethods } from '../src/data/contacts';

describe('FeaturedWorkSection', () => {
  it('renders no more than three work cards', () => {
    render(<FeaturedWorkSection />);
    expect(screen.getAllByRole('article').length).toBeLessThanOrEqual(3);
  });

  it('labels every card as professional or portfolio', () => {
    render(<FeaturedWorkSection />);
    const badges = screen.getAllByText(/^(Professional|Portfolio project)$/);
    expect(badges.length).toBe(Math.min(featuredWork.length, 3));
  });

  it('never presents a portfolio project as employer work', () => {
    render(<FeaturedWorkSection />);
    for (const work of featuredWork.filter((item) => item.type === 'portfolio')) {
      const card = screen.getByRole('article', { name: work.title });
      expect(card).toHaveTextContent('Portfolio project');
      expect(card).not.toHaveTextContent(/^Professional$/);
    }
  });

  it('renders technology tags in an accessible list', () => {
    render(<FeaturedWorkSection />);
    const firstWork = featuredWork[0]!;
    expect(
      screen.getByRole('list', { name: `Technologies used in ${firstWork.title}` }),
    ).toBeInTheDocument();
  });
});

describe('ContactSection', () => {
  it('renders at most three contact cards', () => {
    const { container } = render(<ContactSection />);
    expect(container.querySelectorAll('.contact-card').length).toBeLessThanOrEqual(3);
  });

  it('never renders private contact channels', () => {
    const { container } = render(<ContactSection />);
    expect(container.textContent).not.toMatch(/phone|address|\+\d{7}/i);
  });
});

describe('buildContactMethods', () => {
  it('creates links only for configured channels', () => {
    const methods = buildContactMethods({ githubUrl: 'https://github.com/example' });

    expect(methods.find((m) => m.channel === 'github')?.url).toBe('https://github.com/example');
    expect(methods.find((m) => m.channel === 'email')?.url).toBeUndefined();
    expect(methods.find((m) => m.channel === 'linkedin')?.displayValue).toContain('TO_BE_PROVIDED');
  });

  it('builds a mailto link for a configured public email', () => {
    const methods = buildContactMethods({ email: 'someone@example.com' });
    expect(methods.find((m) => m.channel === 'email')?.url).toBe('mailto:someone@example.com');
  });
});

describe('Footer', () => {
  it('renders the current year, a resume link, and the AI disclaimer', () => {
    render(<Footer />);
    expect(screen.getByText(new RegExp(`${new Date().getFullYear()}`))).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /resume/i })).toBeInTheDocument();
    expect(screen.getByText(/may not capture every detail/i)).toBeInTheDocument();
  });
});
