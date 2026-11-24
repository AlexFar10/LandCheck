import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

// MapLibre needs WebGL, which jsdom lacks. The map has its own checks in the running app.
vi.mock('./MapView', () => ({ MapView: () => <div data-testid="map" /> }))

const layersBody = {
  layers: [
    {
      id: 'sample_flood_history_v0',
      title: 'SAMPLE DATA: flood extent placeholder (not real)',
      hazard_type: 'flood_history',
      default_visible: true,
      observation_date: '2000-01-01',
      sensor: null,
      source_name: 'Land Check sample fixture (not real data)',
      source_url: 'https://example.org/fixture',
      attribution: 'Sample fixture',
      meaning: 'Placeholder polygons.',
      limitations: ['Sample data.'],
      legend: [],
      feature_count: 2,
      coverage: { type: 'Polygon', coordinates: [] },
      method_version: 'fixture-0',
      dataset_version: 'fixture-0',
      sample: true,
    },
  ],
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('loads layers from GET /api/v1/layers and labels them as sample data', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith('/api/v1/layers') ? json(layersBody) : json({}, 404),
    )
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    expect(await screen.findByText(layersBody.layers[0].title)).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('SAMPLE DATA')
    expect(fetchMock.mock.calls.map(([url]) => String(url))).toContain('/api/v1/layers')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows a clear error when the API is not reachable', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('Failed to fetch')
      }),
    )

    render(<App />)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      /Cannot reach the Land Check API.*Check that the API is running/,
    )
    expect(screen.queryByText('Loading layers…')).not.toBeInTheDocument()
    expect(screen.getByTestId('map')).toBeInTheDocument()
  })
})
