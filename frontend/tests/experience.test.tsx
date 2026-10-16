import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { ExperienceSection } from '../src/sections/ExperienceSection';
import { ExperienceItem } from '../src/components/ExperienceItem';
import { professionalExperience, publishableExperience } from '../src/data/experience';
import type { ExperienceItem as ExperienceItemModel } from '../src/types/portfolio';

const approvedRole: ExperienceItemModel = {
  id: 'experience-test-1',
  organization: 'Example Analytics Group',
  startDate: 'Jan 2022',
  endDate: 'Present',
  isCurrent: true,
  role: 'Senior Data Scientist',
  summary: 'Built and operated production machine-learning services.',
  sourceIds: ['resume-chunk-001'],
  approved: true,
};

describe('ExperienceSection', () => {
  it('renders a single Experience heading with no duplicate label or description', () => {
    const { container } = render(<ExperienceSection />);

    expect(screen.getByRole('heading', { level: 2, name: 'Experience' })).toBeInTheDocument();
    expect(container.querySelectorAll('h2')).toHaveLength(1);
    expect(container.querySelector('.section-label, .experience__description')).toBeNull();
    expect(container.textContent).not.toMatch(/where i’ve built/i);
    expect(container.textContent).not.toMatch(
      /selected professional experience building production AI/i,
    );
  });

  it('renders no assistant link in the introduction', () => {
    const { container } = render(<ExperienceSection />);

    expect(container.querySelector('a[href="#assistant"]')).toBeNull();
    expect(container.textContent).not.toMatch(/chat with my ai about my experience/i);
  });

  it('uses the #experience anchor and the alternate background section', () => {
    const { container } = render(<ExperienceSection />);
    const section = container.querySelector('#experience');

    expect(section).not.toBeNull();
    expect(section).toHaveClass('section--alt');
  });

  it('links to no projects destination', () => {
    const { container } = render(<ExperienceSection />);

    expect(container.querySelector('a[href="#projects"]')).toBeNull();
    expect(container.textContent).not.toMatch(/explore portfolio projects|view projects/i);
  });

  it('renders one row per approved record with separators', () => {
    const { container } = render(<ExperienceSection />);
    const approved = publishableExperience(professionalExperience);
    const rows = container.querySelectorAll('.experience-item');

    expect(approved.length).toBeGreaterThan(0);
    expect(rows).toHaveLength(approved.length);
    expect(container.querySelector('.experience__list')).not.toBeNull();
    expect(container.textContent).not.toMatch(/\[[A-Z0-9_]+\]/);
  });

  it('renders every configured organization, role, and date range', () => {
    render(<ExperienceSection />);

    for (const item of publishableExperience(professionalExperience)) {
      expect(screen.getByText(item.organization)).toBeInTheDocument();
      expect(screen.getByRole('heading', { level: 3, name: item.role })).toBeInTheDocument();
      expect(
        screen.getByText(new RegExp(`${item.startDate}\\s*–\\s*${item.endDate}`)),
      ).toBeInTheDocument();
    }
  });

  it('marks exactly the current roles with a CURRENT badge', () => {
    const { container } = render(<ExperienceSection />);
    const currentCount = publishableExperience(professionalExperience).filter(
      (item) => item.isCurrent,
    ).length;

    expect(container.querySelectorAll('.badge--current')).toHaveLength(currentCount);
  });

  it('marks exactly the internships with an INTERNSHIP badge', () => {
    const { container } = render(<ExperienceSection />);
    const internships = publishableExperience(professionalExperience).filter(
      (item) => item.isInternship,
    );

    expect(container.querySelectorAll('.badge--internship')).toHaveLength(internships.length);
    for (const badge of container.querySelectorAll('.badge--internship')) {
      expect(badge).toHaveTextContent('INTERNSHIP');
    }
  });

  it('renders no temporary role-history message', () => {
    const { container } = render(<ExperienceSection />);

    expect(container.querySelector('.experience__pending')).toBeNull();
    expect(container.textContent).not.toMatch(/still being prepared/i);
    expect(container.textContent).not.toMatch(/ask the career assistant in the meantime/i);
  });

  it('renders no card grid or technology tags', () => {
    const { container } = render(<ExperienceSection />);

    expect(container.querySelector('.work-card, .featured-work__grid, .tech-tag')).toBeNull();
  });
});

describe('publishableExperience', () => {
  it('renders approved and complete entries', () => {
    expect(publishableExperience([approvedRole])).toHaveLength(1);
  });

  it('renders every approved record, including a full set of five', () => {
    const five = [1, 2, 3, 4, 5].map((n) => ({ ...approvedRole, id: `experience-${n}` }));
    expect(publishableExperience(five)).toHaveLength(5);
  });

  it('keeps only the approved records in a mixed list', () => {
    const mixed = [
      approvedRole,
      { ...approvedRole, id: 'unapproved', approved: false },
      { ...approvedRole, id: 'incomplete', summary: '' },
    ];
    expect(publishableExperience(mixed).map((item) => item.id)).toEqual(['experience-test-1']);
  });

  it('hides unapproved entries', () => {
    expect(publishableExperience([{ ...approvedRole, approved: false }])).toHaveLength(0);
  });

  it('hides incomplete entries', () => {
    expect(publishableExperience([{ ...approvedRole, role: '' }])).toHaveLength(0);
    expect(publishableExperience([{ ...approvedRole, summary: '   ' }])).toHaveLength(0);
    expect(publishableExperience([{ ...approvedRole, endDate: '' }])).toHaveLength(0);
  });

  it('hides entries containing placeholder tokens', () => {
    expect(
      publishableExperience([
        { ...approvedRole, organization: '[EMPLOYER_1_NAME_TO_BE_PROVIDED]' },
      ]),
    ).toHaveLength(0);
    expect(
      publishableExperience([{ ...approvedRole, role: '[ROLE_TO_BE_PROVIDED]' }]),
    ).toHaveLength(0);
  });
});

describe('ExperienceItem', () => {
  it('renders the organization, dates, role, and summary', () => {
    render(
      <ul>
        <ExperienceItem item={approvedRole} />
      </ul>,
    );

    expect(screen.getByText('Example Analytics Group')).toBeInTheDocument();
    expect(screen.getByText(/Jan 2022 – Present/)).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 3, name: 'Senior Data Scientist' }),
    ).toBeInTheDocument();
    expect(screen.getByText(/production machine-learning services/i)).toBeInTheDocument();
  });

  it('shows a readable CURRENT badge only for current roles', () => {
    const { container, rerender } = render(
      <ul>
        <ExperienceItem item={approvedRole} />
      </ul>,
    );
    const badge = within(container).getByText('CURRENT');
    expect(badge).toHaveClass('badge--current');

    rerender(
      <ul>
        <ExperienceItem item={{ ...approvedRole, isCurrent: false, endDate: 'Dec 2023' }} />
      </ul>,
    );
    expect(within(container).queryByText('CURRENT')).not.toBeInTheDocument();
  });

  it('wraps long organization and role names without exposing source IDs', () => {
    const longToken = `Organization${'Name'.repeat(40)}`;
    const { container } = render(
      <ul>
        <ExperienceItem item={{ ...approvedRole, organization: longToken, role: longToken }} />
      </ul>,
    );

    expect(container.querySelector('.experience-item__organization')).toHaveTextContent(longToken);
    expect(container.querySelector('.experience-item__role')).toHaveTextContent(longToken);
    expect(container.textContent).not.toContain('resume-chunk-001');
  });

  it('renders no technology tags in a professional experience row', () => {
    const { container } = render(
      <ul>
        <ExperienceItem item={approvedRole} />
      </ul>,
    );

    expect(container.querySelector('.tech-tag')).toBeNull();
  });
});
