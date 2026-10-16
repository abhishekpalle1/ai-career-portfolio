import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HeroSection } from '../src/sections/HeroSection';
import { MetricsSection } from '../src/sections/MetricsSection';
import { profile } from '../src/data/profile';
import { careerMetrics } from '../src/data/metrics';

describe('HeroSection', () => {
  it('renders the name as the dominant heading', () => {
    render(<HeroSection />);
    expect(screen.getByRole('heading', { level: 1, name: profile.fullName })).toBeInTheDocument();
  });

  it('renders the professional title and value proposition from typed content', () => {
    render(<HeroSection />);
    expect(screen.getByText(profile.professionalTitle)).toBeInTheDocument();
    expect(screen.getByText(profile.valueProposition)).toBeInTheDocument();
  });

  it('falls back to initials when no photo is supplied', () => {
    render(<HeroSection />);
    if (profile.photoUrl === null) {
      expect(screen.getByText(profile.initials)).toBeInTheDocument();
      expect(screen.queryByRole('img')).not.toBeInTheDocument();
    }
  });

  it('scrolls to the assistant and contact sections from the hero buttons', async () => {
    const user = userEvent.setup();
    const assistant = document.createElement('section');
    assistant.id = 'assistant';
    const contact = document.createElement('section');
    contact.id = 'contact';
    document.body.append(assistant, contact);

    const assistantSpy = vi.spyOn(assistant, 'scrollIntoView');
    const contactSpy = vi.spyOn(contact, 'scrollIntoView');

    render(<HeroSection />);
    await user.click(screen.getByRole('button', { name: /chat with my ai/i }));
    await user.click(screen.getByRole('button', { name: /get in touch/i }));

    expect(assistantSpy).toHaveBeenCalled();
    expect(contactSpy).toHaveBeenCalled();

    assistant.remove();
    contact.remove();
  });
});

describe('MetricsSection', () => {
  it('renders at most four metrics with their labels', () => {
    const { container } = render(<MetricsSection />);
    const rendered = container.querySelectorAll('.metric');
    expect(rendered.length).toBe(Math.min(careerMetrics.length, 4));
    expect(rendered.length).toBeLessThanOrEqual(4);
  });

  it('exposes the metrics band under an accessible region label', () => {
    render(<MetricsSection />);
    expect(screen.getByRole('region', { name: 'Career metrics' })).toBeInTheDocument();
  });
});
