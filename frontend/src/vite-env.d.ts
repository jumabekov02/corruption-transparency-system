/// <reference types="vite/client" />

// Tells TypeScript about our custom environment variable.
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
