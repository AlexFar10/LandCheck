import { useCallback, useState } from 'react'
import { analyze } from './api'
import { ParcelMap } from './ParcelMap'
import { ResultsList } from './ResultsList'
import type { PolygonGeometry, RiskResult } from './types'

export default function App() {
  const [parcel, setParcel] = useState<PolygonGeometry | null>(null)
  const [results, setResults] = useState<RiskResult[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const onParcelChange = useCallback((next: PolygonGeometry | null) => {
    setParcel(next)
    setResults(null)
  }, [])

  async function onAnalyze() {
    if (!parcel) return
    setLoading(true)
    setError(null)
    try {
      setResults((await analyze(parcel)).results)
    } catch (err) {
      setResults(null)
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <ParcelMap onChange={onParcelChange} />
      <aside className="panel">
        <h1>Land Check</h1>
        <p>{parcel ? 'Parcel drawn.' : 'Draw a parcel with the polygon tool on the map.'}</p>
        <button onClick={onAnalyze} disabled={!parcel || loading}>
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>
        {error && <p className="error">{error}</p>}
        {results && <ResultsList results={results} />}
      </aside>
    </div>
  )
}
