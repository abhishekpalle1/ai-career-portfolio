import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { HeroSection } from '../src/sections/HeroSection';
import { HeroProofPoint } from '../src/components/HeroProofPoint';
import { profile } from '../src/data/profile';
import { contactMethods } from '../src/data/contacts';
import { heroProofPoints, publishableProofPoints } from '../src/data/heroProofPoints';
import type { HeroProofPoint as HeroProofPointModel } from '../src/types/portfolio';

const baseProofPoint: HeroProofPointModel = {
  id: 'proof-test',
  value: '8+ yrs',
  label: 'Engineering Experience',
  verified: true,
  approved: true,
  sourceIds: ['approved-career-profile'],
};

const HERO_DESCRIPTION =
  'AI & ML Engineer building production-grade pipelines, ML systems, LLM applications, and data-driven analytics.';

describe('Landing page content', () => {
  it('renders no category eyebrow label above the proof points', () => {
    const { container } = render(<HeroSection />);

    expect(container.querySelector('.section-label')).toBeNull();
    expect(container.textContent).not.toMatch(/DATA & AI ENGINEERING/i);
    expect(container.textContent).not.toMatch(/AI & MACHINE LEARNING SYSTEMS/i);
  });

  it('renders both numeric proof points with their labels', () => {
    render(<HeroSection />);

    expect(screen.getByText('8+ yrs')).toBeInTheDocument();
    expect(screen.getByText(/engineering experience/i)).toBeInTheDocument();
    expect(screen.getByText('15+')).toBeInTheDocument();
    expect(screen.getByText(/projects delivered/i)).toBeInTheDocument();
  });

  it('does not render the former capability blocks', () => {
    const { container } = render(<HeroSection />);

    expect(container.textContent).not.toMatch(/RAG & Evaluation/i);
    expect(container.textContent).not.toMatch(/LLM systems, inference pipelines/i);
    expect(container.textContent).not.toMatch(/Grounded retrieval, citations/i);
  });

  it('renders the greeting exactly as “Hello, it’s”', () => {
    const { container } = render(<HeroSection />);

    expect(screen.getByText('Hello, it’s')).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/Hello, I’m/);
  });

  it('renders the name as the dominant heading', () => {
    render(<HeroSection />);

    expect(screen.getByRole('heading', { level: 1, name: 'Abhishek Palle' })).toBeInTheDocument();
  });

  it('renders the exact professional description with an emphasized lead', () => {
    const { container } = render(<HeroSection />);
    const description = container.querySelector('.hero__description') as HTMLElement;

    expect(description).toHaveTextContent(HERO_DESCRIPTION);
    expect(description.querySelector('strong')).toHaveTextContent('AI & ML Engineer');
    expect(profile.valueProposition).toBe(HERO_DESCRIPTION);
  });

  it('removes the previous description wording', () => {
    const { container } = render(<HeroSection />);

    expect(container.textContent).not.toMatch(/reliable production AI systems/i);
    expect(container.textContent).not.toMatch(/evaluation frameworks/i);
    expect(container.textContent).not.toMatch(/cloud-native machine-learning pipelines/i);
  });

  it('keeps the hero left-aligned with no avatar or monogram', () => {
    const { container } = render(<HeroSection />);

    expect(container.querySelector('.hero__inner')).not.toBeNull();
    expect(container.querySelector('.hero__avatar, .hero__photo, .hero__initials')).toBeNull();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(container.textContent).not.toMatch(/\bAP\b/);
  });

  it('renders the value proposition from typed content', () => {
    const { container } = render(<HeroSection />);
    expect(container.querySelector('.hero__description')).toHaveTextContent(
      profile.valueProposition,
    );
  });

  it('orders Explore Experience before Chat with My AI with the right targets', () => {
    const { container } = render(<HeroSection />);
    const actions = Array.from(
      container.querySelectorAll('.hero__actions a'),
    ) as HTMLAnchorElement[];

    expect(actions.map((a) => a.getAttribute('href'))).toEqual(['#experience', '#assistant']);
    expect(actions[0]).toHaveTextContent('Explore Experience');
    expect(actions[1]).toHaveTextContent('Chat with My AI');
  });

  it('puts the down arrow on Chat with My AI and none on Explore Experience', () => {
    const { container } = render(<HeroSection />);
    const actions = Array.from(
      container.querySelectorAll('.hero__actions a'),
    ) as HTMLAnchorElement[];

    expect(actions[0]!.textContent).toBe('Explore Experience');
    expect(actions[0]!.querySelector('[aria-hidden="true"]')).toBeNull();
    expect(actions[1]!.textContent).toContain('↓');
    expect(actions[1]!.textContent).not.toContain('→');
  });

  it('renders no résumé, CV, or projects action', () => {
    const { container } = render(<HeroSection />);

    expect(container.textContent).not.toMatch(/download cv|view projects|resume/i);
  });

  it('renders configured social links as icon-only links with accessible names', () => {
    const { container } = render(<HeroSection />);
    const list = container.querySelector('.hero__links');

    expect(contactMethods.length).toBeGreaterThan(0);
    expect(list?.children).toHaveLength(contactMethods.length);

    for (const contact of contactMethods) {
      const link = screen.getByRole('link', { name: new RegExp(`^${contact.label}`) });
      expect(link).toHaveAttribute('href', contact.url);
      expect(link).toHaveClass('icon-link');
      expect(link.textContent).toBe('');
      expect(link.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
    }
    expect(container.textContent).not.toMatch(/\[[A-Z0-9_]+\]/);
  });

  it('opens external profile links safely in a new tab', () => {
    render(<HeroSection />);

    for (const contact of contactMethods.filter((c) => c.external)) {
      const link = screen.getByRole('link', { name: new RegExp(`^${contact.label}`) });
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    }
  });
});

describe('publishableProofPoints', () => {
  it('publishes both configured numeric proof points', () => {
    const published = publishableProofPoints(heroProofPoints);

    expect(published).toHaveLength(2);
    expect(published.map((point) => point.value)).toEqual(['8+ yrs', '15+']);
  });

  it('marks both configured proof points verified and approved with a source ID', () => {
    for (const point of heroProofPoints) {
      expect(point.verified).toBe(true);
      expect(point.approved).toBe(true);
      expect(point.sourceIds.length).toBeGreaterThan(0);
    }
  });

  it('hides unverified or unapproved entries', () => {
    expect(publishableProofPoints([{ ...baseProofPoint, verified: false }])).toHaveLength(0);
    expect(publishableProofPoints([{ ...baseProofPoint, approved: false }])).toHaveLength(0);
  });

  it('hides placeholder values and labels', () => {
    expect(
      publishableProofPoints([{ ...baseProofPoint, value: '[SUPPORTED_VALUE]' }]),
    ).toHaveLength(0);
    expect(
      publishableProofPoints([{ ...baseProofPoint, label: '[METRIC_1_LABEL_TO_BE_PROVIDED]' }]),
    ).toHaveLength(0);
  });

  it('requires a retained source ID before publishing a numeric value', () => {
    expect(publishableProofPoints([{ ...baseProofPoint, sourceIds: [] }])).toHaveLength(0);
  });

  it('never publishes more than two entries', () => {
    const many = [1, 2, 3, 4].map((n) => ({ ...baseProofPoint, id: `proof-${n}` }));
    expect(publishableProofPoints(many)).toHaveLength(2);
  });
});

describe('HeroProofPoint', () => {
  it('renders the value above the label and hides raw source IDs', () => {
    const { container } = render(<HeroProofPoint proofPoint={baseProofPoint} />);

    expect(container.querySelector('.proof-point__value')).toHaveTextContent('8+ yrs');
    expect(container.querySelector('.proof-point__label')).toHaveTextContent(
      'Engineering Experience',
    );
    expect(container.textContent).not.toContain('approved-career-profile');
  });

  it('renders no card wrapper or description block', () => {
    const { container } = render(<HeroProofPoint proofPoint={baseProofPoint} />);

    expect(container.querySelector('.proof-point__description')).toBeNull();
    expect(container.querySelector('.card, .metric, .metrics')).toBeNull();
  });
});
