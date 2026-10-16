import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import App from '../src/App';

describe('App', () => {
  it('renders every required section anchor', () => {
    vi.stubGlobal('fetch', vi.fn());
    const { container } = render(<App />);

    for (const id of ['home', 'work', 'assistant', 'contact']) {
      expect(container.querySelector(`#${id}`)).not.toBeNull();
    }
  });

  it('uses a single h1 and section-level h2 headings', () => {
    vi.stubGlobal('fetch', vi.fn());
    render(<App />);

    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.getAllByRole('heading', { level: 2 }).length).toBeGreaterThanOrEqual(3);
  });

  it('provides a skip link and anchor navigation', () => {
    vi.stubGlobal('fetch', vi.fn());
    render(<App />);

    expect(screen.getByRole('link', { name: /skip to main content/i })).toBeInTheDocument();
    const nav = screen.getByRole('navigation', { name: /section navigation/i });
    expect(within(nav).getAllByRole('link')).toHaveLength(4);
  });
});
