import { setWorkerUrl } from 'maplibre-gl'
// MapLibre loads its worker next to its own module URL, which breaks once Vite pre-bundles it.
// Hand it a worker that Vite bundles itself, so dev and production builds both work.
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'

setWorkerUrl(workerUrl)
