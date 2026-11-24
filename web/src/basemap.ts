import type { StyleSpecification } from 'maplibre-gl'

// Pechea, Galați County (PRD decision D-01), as [lon, lat].
export const PILOT_CENTER: [number, number] = [27.8, 45.63]
export const PILOT_ZOOM = 11

export const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'

// Interim basemap: OpenStreetMap standard raster tiles. The final provider is open (D-12).
// The OSM tile usage policy allows light use like development, not heavy production traffic.
export const BASEMAP_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      maxzoom: 19,
      attribution: OSM_ATTRIBUTION,
    },
  },
  layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
}
