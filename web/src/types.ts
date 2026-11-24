// Mirrors the API contract in docs/PRD.md Section 12.
import type { Geometry } from 'geojson'

export interface Health {
  status: 'ok' | 'error'
  version: string
  git_commit: string
  dataset_id: string | null
  dataset_version: string | null
  sample: boolean | null
}

export interface LegendEntry {
  label: string
  color: string
}

export interface Layer {
  id: string
  title: string
  hazard_type: string
  default_visible: boolean
  observation_date: string
  sensor: string | null
  source_name: string
  source_url: string
  attribution: string
  meaning: string
  limitations: string[]
  legend: LegendEntry[]
  feature_count: number
  coverage: Geometry
  method_version: string
  dataset_version: string
  sample: boolean
}

export interface LayersResponse {
  layers: Layer[]
}

export interface ApiErrorBody {
  error: { code: string; message: string; details: Record<string, unknown> }
}
