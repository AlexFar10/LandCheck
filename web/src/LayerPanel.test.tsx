import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { LayerPanel } from './LayerPanel'
import type { Health, Layer } from './types'

const health: Health = {
  status: 'ok',
  version: '0.1.0',
  git_commit: 'abc',
  dataset_id: 'sample-fixture',
  dataset_version: 'fixture-0',
  sample: true,
}

const layer: Layer = {
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
  legend: [{ label: 'Sample polygon', color: '#9333EA' }],
  feature_count: 2,
  coverage: { type: 'Polygon', coordinates: [] },
  method_version: 'fixture-0',
  dataset_version: 'fixture-0',
  sample: true,
}

describe('LayerPanel', () => {
  it('lists layers from the API with date and source link', () => {
    render(<LayerPanel health={health} layers={[layer]} error={null} />)
    expect(screen.getByText(layer.title)).toBeInTheDocument()
    expect(screen.getByText('2000-01-01')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: layer.source_name })).toHaveAttribute(
      'href',
      layer.source_url,
    )
  })

  it('labels sample data clearly', () => {
    render(<LayerPanel health={health} layers={[layer]} error={null} />)
    expect(screen.getByRole('status')).toHaveTextContent('SAMPLE DATA')
    expect(screen.getByText('Sample')).toBeInTheDocument()
  })

  it('has no sample banner for a real dataset', () => {
    const real = { ...layer, sample: false, title: 'Flood extent' }
    render(<LayerPanel health={{ ...health, sample: false }} layers={[real]} error={null} />)
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('renders null as "Not available", never 0', () => {
    render(<LayerPanel health={health} layers={[layer]} error={null} />)
    expect(screen.getByText('Not available')).toBeInTheDocument()
    expect(screen.queryByText('0')).not.toBeInTheDocument()
  })

  it('shows API errors instead of an empty list', () => {
    render(<LayerPanel health={null} layers={null} error="The dataset is not available." />)
    expect(screen.getByRole('alert')).toHaveTextContent('The dataset is not available.')
    expect(screen.queryByText('Loading layers…')).not.toBeInTheDocument()
  })
})
