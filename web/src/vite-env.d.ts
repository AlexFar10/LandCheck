/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Optional API origin. Unset means same origin (dev proxy or production). */
  readonly VITE_API_URL?: string
}
