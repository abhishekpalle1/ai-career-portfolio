/**
 * Content gating shared by every visible section.
 *
 * Source configuration files may hold bracketed placeholders while career
 * content is being approved, but nothing bracketed may ever reach the page.
 */
const PLACEHOLDER_PATTERN = /\[[A-Z0-9_]+\]/;

export function isPublishableText(value: string | undefined): value is string {
  return typeof value === 'string' && value.trim().length > 0 && !PLACEHOLDER_PATTERN.test(value);
}
