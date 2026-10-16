import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../src/App';

function renderApp() {
  vi.stubGlobal('fetch', vi.fn());
  return render(<App />);
}

describe('App shell', () => {
  it('renders the page anchors and the footer', () => {
    const { container } = renderApp();

    for (const id of ['home', 'experience', 'assistant']) {
      expect(container.querySelector(`#${id}`)).not.toBeNull();
    }
    expect(container.querySelector('footer.footer')).not.toBeNull();
  });

  it('uses a single h1 and section-level h2 headings', () => {
    renderApp();

    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.getAllByRole('heading', { level: 2 }).length).toBeGreaterThanOrEqual(2);
  });

  it('provides a skip link into the main landmark', () => {
    renderApp();

    expect(screen.getByRole('link', { name: /skip to main content/i })).toHaveAttribute(
      'href',
      '#main',
    );
    expect(screen.getByRole('main')).toHaveAttribute('id', 'main');
  });
});

describe('removed top navigation', () => {
  it('renders no header bar or section navigation', () => {
    const { container } = renderApp();

    expect(container.querySelector('header, .site-header, .site-nav')).toBeNull();
    expect(
      screen.queryByRole('navigation', { name: /section navigation/i }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /menu/i })).not.toBeInTheDocument();
  });

  it('renders no contact section or removed résumé affordance', () => {
    const { container } = renderApp();

    expect(container.querySelector('#contact, .contact, a[href="#contact"]')).toBeNull();
    expect(screen.queryByRole('link', { name: /resume|cv/i })).not.toBeInTheDocument();
    expect(container.querySelector('a[href$=".pdf"]')).toBeNull();
    expect(container.textContent).not.toMatch(/download cv/i);
  });

  it('renders no Projects navigation item, anchor, section, or card', () => {
    const { container } = renderApp();

    expect(screen.queryByRole('link', { name: /projects/i })).not.toBeInTheDocument();
    expect(container.querySelector('#projects, a[href="#projects"]')).toBeNull();
    expect(container.querySelector('.projects, .project-card, .project-item')).toBeNull();
    expect(container.textContent).not.toMatch(/explore (portfolio )?projects|view projects/i);
  });
});

describe('placeholder policy', () => {
  it('never renders a bracketed placeholder token', () => {
    const { container } = renderApp();

    expect(container.textContent).not.toMatch(/\[[A-Z0-9_]+\]/);
  });

  it('never renders removed placeholder or availability copy', () => {
    const { container } = renderApp();

    expect(container.textContent).not.toMatch(/still being prepared/i);
    expect(container.textContent).not.toMatch(/being finalized/i);
    expect(container.textContent).not.toMatch(/let’s connect/i);
    expect(container.textContent).not.toMatch(/open to relevant ML\/AI opportunities/i);
    expect(container.textContent).not.toMatch(
      /selected professional experience building production AI/i,
    );
  });
});
