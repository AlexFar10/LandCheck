import type { AnalyzeResponse, PolygonGeometry } from './types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function analyze(parcel: PolygonGeometry): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_URL}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(parcel),
  })
  if (!response.ok) {
    // Fail loudly: surface the backend's message instead of showing empty results.
    throw new Error(`Analyze failed (${response.status}): ${await response.text()}`)
  }
  return (await response.json()) as AnalyzeResponse
}
