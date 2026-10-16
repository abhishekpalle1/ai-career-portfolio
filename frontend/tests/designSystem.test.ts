import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

/**
 * jsdom performs no layout, so document width cannot be measured here. These
 * tests lock in the Modern Forest Minimal token contract and the CSS rules that
 * stop intrinsic content widths from forcing document-level horizontal
 * scrolling. Measured width verification happens in a real browser.
 */
const read = (file: string): string =>
  readFileSync(resolve(process.cwd(), 'src/styles', file), 'utf8');

const tokens = read('tokens.css');
const css = read('global.css');

const rule = (selector: string, source = css): string => {
  const match = source.match(
    new RegExp(`(^|\\n)${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\\{([^}]*)\\}`),
  );
  return match?.[2] ?? '';
};

describe('Modern Forest Minimal design tokens', () => {
  it('defines the bright neutral, forest, sage, and terracotta palette', () => {
    const expected: Record<string, string> = {
      '--color-background': '#fdfdfb',
      '--color-background-alt': '#f3f5f2',
      '--color-surface': '#ffffff',
      '--color-surface-muted': '#f7f8f6',
      '--color-text-primary': '#17211c',
      '--color-text-secondary': '#59645e',
      '--color-text-muted': '#7a847e',
      '--color-primary': '#176044',
      '--color-primary-hover': '#104b34',
      '--color-primary-soft': '#e5f0e9',
      '--color-accent': '#bd5738',
      '--color-accent-hover': '#9e4229',
      '--color-accent-soft': '#f7e8e2',
      '--color-border': '#dce2dd',
      '--color-border-strong': '#bdc9c0',
      '--color-success': '#2d7c54',
      '--color-success-soft': '#e3f3e9',
      '--color-danger': '#a83c3c',
      '--color-white': '#ffffff',
      '--color-footer': '#102d22',
    };

    for (const [token, value] of Object.entries(expected)) {
      expect(tokens).toContain(`${token}: ${value};`);
    }
  });

  it('removes every earlier blue, navy, and warm-ivory brand color', () => {
    const retired = [
      '#2563eb',
      '#1d4ed8',
      '#eaf1ff',
      '#0f172a',
      '#f5f7ff',
      '#60a5fa',
      '#f8f6f0',
      '#eeeee6',
      '#224c3a',
      '#a64b2a',
      '#19231d',
    ];

    for (const color of retired) {
      expect(tokens).not.toContain(color);
      expect(css).not.toContain(color);
    }
  });

  it('preserves the Phase 1 font stack', () => {
    expect(tokens).toContain('--font-sans:');
    expect(tokens).toContain('Inter, ui-sans-serif, system-ui');
  });

  it('centers the page on a ~1180px container with responsive padding', () => {
    expect(tokens).toContain('--page-max-width: 1180px;');
    expect(tokens).toContain('--page-padding-inline: 32px;');
    expect(tokens).toContain('--page-padding-inline: 18px;');
    expect(rule('.container')).toContain('margin: 0 auto');
    expect(rule('.container')).toContain('width: 100%');
  });

  it('applies the required page color sequence', () => {
    expect(rule('body')).toContain('background-color: var(--color-background)');
    expect(rule('.section--alt')).toContain('background: var(--color-background-alt)');
    expect(rule('.footer')).toContain('background: var(--color-footer)');
  });

  it('defines no contact-section or top-navigation styling after their removal', () => {
    expect(css).not.toMatch(/\.contact/);
    expect(css).not.toMatch(/\.site-header|\.site-nav/);
  });
});

describe('assistant window styling', () => {
  it('uses a white window with a white header and no dark-green band', () => {
    expect(rule('.chat-panel')).toContain('background: var(--color-surface)');
    expect(rule('.chat-panel')).toContain('border: 1px solid var(--color-border)');
    expect(rule('.chat-panel__header')).toContain('background: var(--color-surface)');
    expect(rule('.chat-panel__header')).not.toContain('var(--color-primary)');
  });

  it('uses the muted conversation surface and a bounded assistant width', () => {
    expect(rule('.chat-panel__transcript')).toContain('background: var(--color-surface-muted)');
    expect(rule('.chat-panel')).toContain('max-width: var(--assistant-max-width)');
    expect(tokens).toContain('--assistant-max-width: 980px;');
  });

  it('stacks suggested questions as full-width rows, never pills', () => {
    const list = rule('.chat-panel__suggestions-list');
    expect(list).toContain('flex-direction: column');
    expect(list).not.toContain('flex-wrap: wrap');

    const question = rule('.suggested-question');
    expect(question).toContain('width: 100%');
    expect(question).toContain('text-align: left');
    expect(question).toContain('border-radius: var(--radius-button)');
    expect(question).not.toContain('border-radius: 999px');
  });

  it('keeps forest submit and badge colors with terracotta citation markers', () => {
    expect(rule('.chat-panel__submit')).toContain('background: var(--color-primary)');
    expect(rule('.chat-message__badge')).toContain('background: var(--color-primary)');
    expect(rule('.citations__marker')).toContain('color: var(--color-accent)');
  });

  it('defines no permanent evidence panel styling', () => {
    expect(css).not.toMatch(/\.evidence/);
    expect(css).not.toMatch(/chat-panel__body/);
  });
});

describe('horizontal overflow guards', () => {
  it('applies the border-box model to every element', () => {
    expect(css).toMatch(/\*,\s*\*::before,\s*\*::after\s*\{\s*box-sizing:\s*border-box;/);
  });

  it('never sizes page sections with 100vw', () => {
    expect(css).not.toMatch(/100vw/);
  });

  it('allows every grid track to shrink below its content', () => {
    const declarations = css.match(/grid-template-columns:[^;]*;/g) ?? [];
    expect(declarations.length).toBeGreaterThan(0);
    for (const declaration of declarations) {
      expect(declaration).toContain('minmax(0,');
    }
  });

  it('lets grid and flex children shrink', () => {
    for (const selector of [
      '.experience-item',
      '.experience-item__header',
      '.experience-item__organization',
      '.chat-message',
      '.chat-message__bubble',
      '.chat-panel__input',
      '.chat-panel__form',
      '.proof-point',
      '.hero__actions',
      '.hero__links',
      '.footer__links',
    ]) {
      expect(rule(selector)).toContain('min-width: 0');
    }
  });

  it('wraps long organization, role, question, excerpt, and link text', () => {
    for (const selector of [
      '.experience-item__organization',
      '.experience-item__role',
      '.experience-item__summary',
      '.drawer__excerpt',
      '.suggested-question',
      '.citations__button',
      '.text-link',
      '.hero__name',
      '.proof-point__value',
    ]) {
      expect(rule(selector)).toContain('overflow-wrap: anywhere');
    }
    expect(rule('body')).toContain('overflow-wrap: break-word');
  });

  it('keeps the root safeguard non-clipping so focus outlines survive', () => {
    expect(rule('html')).toContain('overflow-x: clip');
    expect(rule('html')).not.toContain('overflow-x: hidden');
    expect(css).not.toMatch(/body\s*\{[^}]*overflow-x:\s*hidden/);
  });

  it('keeps visible focus styling and reduced-motion support', () => {
    expect(rule(':focus-visible')).toContain('outline: 3px solid');
    expect(rule('.chat-panel__input:focus-visible')).toContain('outline: 3px solid');
    expect(css).toContain('@media (prefers-reduced-motion: reduce)');
  });
});
