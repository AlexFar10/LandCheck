import { useEffect } from 'react'
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import type L from 'leaflet'
import '@geoman-io/leaflet-geoman-free'
import type { PolygonGeometry } from './types'

// Centre of Timiș county (pilot region).
const TIMIS_CENTER: [number, number] = [45.75, 21.23]
const TIMIS_ZOOM = 9

type OnChange = (parcel: PolygonGeometry | null) => void

function DrawControl({ onChange }: { onChange: OnChange }) {
  const map = useMap()

  useEffect(() => {
    map.pm.addControls({
      position: 'topleft',
      drawMarker: false,
      drawCircleMarker: false,
      drawPolyline: false,
      drawRectangle: false,
      drawCircle: false,
      drawText: false,
      cutPolygon: false,
      rotateMode: false,
    })

    const emit = (layer: L.Polygon) => onChange(layer.toGeoJSON().geometry as PolygonGeometry)

    map.on('pm:create', (event) => {
      const layer = event.layer as L.Polygon
      // One parcel at a time: remove older shapes.
      map.pm.getGeomanLayers().forEach((other) => {
        if (other !== layer) other.remove()
      })
      layer.on('pm:edit', () => emit(layer))
      emit(layer)
    })
    map.on('pm:remove', () => onChange(null))

    return () => {
      map.pm.removeControls()
      map.off('pm:create')
      map.off('pm:remove')
    }
  }, [map, onChange])

  return null
}

export function ParcelMap({ onChange }: { onChange: OnChange }) {
  return (
    <MapContainer center={TIMIS_CENTER} zoom={TIMIS_ZOOM} className="map">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <DrawControl onChange={onChange} />
    </MapContainer>
  )
}
