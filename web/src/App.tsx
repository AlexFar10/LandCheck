import { useEffect, useState } from 'react'
import { getHealth, getLayers } from './api'
import { LayerPanel } from './LayerPanel'
import { MapView } from './MapView'
import type { Health, Layer } from './types'

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [layers, setLayers] = useState<Layer[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    // The layer list drives the panel. Its failure is the error the user sees.
    getLayers()
      .then((response) => {
        if (!cancelled) setLayers(response.layers)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      })
    // Health only adds the version line, so its failure is not shown separately.
    getHealth()
      .then((response) => {
        if (!cancelled) setHealth(response)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="app">
      <MapView layers={layers ?? []} />
      <LayerPanel health={health} layers={layers} error={error} />
    </div>
  )
}
