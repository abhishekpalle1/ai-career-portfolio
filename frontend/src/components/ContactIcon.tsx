import type { ContactChannel } from '../types/portfolio';

interface ContactIconProps {
  channel: ContactChannel;
}

/** Decorative glyphs; the surrounding link carries the accessible name. */
export function ContactIcon({ channel }: ContactIconProps) {
  const shared = {
    viewBox: '0 0 24 24',
    width: 20,
    height: 20,
    'aria-hidden': true,
    focusable: false,
  } as const;

  if (channel === 'email') {
    return (
      <svg
        {...shared}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="2.75" y="5" width="18.5" height="14" rx="2.5" />
        <path d="m3.5 7.5 8.5 5.8 8.5-5.8" />
      </svg>
    );
  }

  if (channel === 'linkedin') {
    return (
      <svg {...shared} fill="currentColor">
        <path d="M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5ZM3.2 9.25h3.56V21H3.2V9.25Zm6.05 0h3.41v1.6h.05c.48-.9 1.65-1.86 3.4-1.86 3.63 0 4.3 2.3 4.3 5.3V21h-3.55v-5.94c0-1.42-.03-3.24-2-3.24-2 0-2.31 1.54-2.31 3.14V21H9.25V9.25Z" />
      </svg>
    );
  }

  return (
    <svg {...shared} fill="currentColor">
      <path d="M12 2.2a9.8 9.8 0 0 0-3.1 19.1c.49.09.67-.21.67-.47 0-.24-.01-.86-.01-1.69-2.73.59-3.3-1.31-3.3-1.31-.45-1.14-1.09-1.44-1.09-1.44-.89-.61.07-.6.07-.6.98.07 1.5 1.01 1.5 1.01.88 1.5 2.3 1.07 2.86.82.09-.64.34-1.07.62-1.32-2.18-.25-4.47-1.09-4.47-4.85 0-1.07.38-1.95 1.01-2.63-.1-.25-.44-1.25.1-2.6 0 0 .82-.27 2.7 1a9.4 9.4 0 0 1 4.9 0c1.88-1.27 2.7-1 2.7-1 .54 1.35.2 2.35.1 2.6.63.68 1.01 1.56 1.01 2.63 0 3.77-2.3 4.6-4.49 4.84.35.31.67.91.67 1.84 0 1.33-.01 2.4-.01 2.72 0 .27.18.57.68.47A9.8 9.8 0 0 0 12 2.2Z" />
    </svg>
  );
}
