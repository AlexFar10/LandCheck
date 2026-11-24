import { useEffect, useRef } from 'react'
import { Map as MapLibreMap, NavigationControl, ScaleControl } from 'maplibre-gl'
import './maplibre-worker'
import { BASEMAP_STYLE, PILOT_CENTER, PILOT_ZOOM } from './basemap'
import type { Layer } from './types'

const COVERAGE_COLOR = '#334155'

/** MapLibre map centred on the pilot. Draws each layer's coverage boundary. */
export function MapView({ layers }: { layers: Layer[] }) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<MapLibreMap | null>(null)

  useEffect(() => {
    if (!container.current) return
    const instance = new MapLibreMap({
      container: container.current,
      style: BASEMAP_STYLE,
      center: PILOT_CENTER,
      zoom: PILOT_ZOOM,
      // Expanded, so the basemap attribution stays visible.
      attributionControl: { compact: false },
    })
    instance.addControl(new NavigationControl(), 'top-left')
    instance.addControl(new ScaleControl(), 'bottom-left')
    map.current = instance
    return () => {
      instance.remove()
      map.current = null
    }
  }, [])

  useEffect(() => {
    const instance = map.current
    if (!instance) return
    const draw = () => {
      for (const layer of layers) {
        const id = `coverage-${layer.id}`
        if (instance.getSource(id)) continue
        instance.addSource(id, { type: 'geojson', data: layer.coverage })
        instance.addLayer({
          id,
          type: 'line',
          source: id,
          paint: { 'line-color': COVERAGE_COLOR, 'line-width': 2, 'line-dasharray': [2, 2] },
        })
      }
    }
    if (instance.isStyleLoaded()) draw()
    else instance.once('load', draw)
  }, [layers])

  return <div ref={container} className="map" data-testid="map" />
}
