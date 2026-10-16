/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_BASE_PATH?: string;
  readonly VITE_GITHUB_URL?: string;
  readonly VITE_LINKEDIN_URL?: string;
  readonly VITE_PUBLIC_EMAIL?: string;
  readonly VITE_SHOW_MOCK_NOTICE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
