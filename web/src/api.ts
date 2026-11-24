import type { ApiErrorBody, Health, LayersResponse } from './types'

// VITE_API_URL unset (default): same origin. Vite proxies /api and /health to the API in dev,
// and FastAPI serves the app in production. Set it to call an API on another origin directly,
// e.g. http://127.0.0.1:3000, and allow this origin in LANDCHECK_CORS_ORIGINS.
export const API_BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')

export const API_UNREACHABLE = 'API_UNREACHABLE'

export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

function unreachable(status: number): ApiError {
  const where = API_BASE || 'this site (dev proxy to the API on PORT)'
  return new ApiError(
    status,
    API_UNREACHABLE,
    `Cannot reach the Land Check API at ${where}. Check that the API is running.`,
  )
}

async function getJson<T>(path: string): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { headers: { Accept: 'application/json' } })
  } catch {
    // Network failure, refused connection or CORS rejection.
    throw unreachable(0)
  }
  if (!response.ok) {
    // Fail loudly: surface the API's error object instead of showing an empty map.
    let body: Partial<ApiErrorBody> | null = null
    try {
      body = (await response.json()) as Partial<ApiErrorBody>
    } catch {
      body = null
    }
    if (body?.error) throw new ApiError(response.status, body.error.code, body.error.message)
    // The API always answers with JSON, so a bare gateway error means the dev proxy or a
    // load balancer could not reach it.
    if ([502, 503, 504].includes(response.status)) throw unreachable(response.status)
    throw new ApiError(
      response.status,
      'HTTP_ERROR',
      `Request to ${path} failed (${response.status}).`,
    )
  }
  return (await response.json()) as T
}

export const getHealth = () => getJson<Health>('/health')
export const getLayers = () => getJson<LayersResponse>('/api/v1/layers')
