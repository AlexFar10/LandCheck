// Mirrors contracts/result.schema.json (requirements section 6.1).
export type Level = 'Low' | 'Medium' | 'High' | 'Unknown'

export interface RiskResult {
  risk: string
  level: Level
  value: number | null
  unit: string
  confidence: number | null
  summary: string
  sources: { name: string; url?: string | null }[]
  date_range: { start: string; end: string }
}

export interface AnalyzeResponse {
  results: RiskResult[]
}

export interface PolygonGeometry {
  type: 'Polygon'
  coordinates: number[][][]
}
