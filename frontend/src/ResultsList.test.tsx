import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ResultsList } from './ResultsList'
import type { RiskResult } from './types'
import floodHistory from '../../contracts/mocks/flood_history.json'
import groundStability from '../../contracts/mocks/ground_stability.json'

const results = [floodHistory, groundStability] as RiskResult[]

describe('ResultsList', () => {
  it('shows one row per result with its level', () => {
    render(<ResultsList results={results} />)
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(screen.getByText('Medium')).toBeInTheDocument()
  })

  it('shows Unknown with "no data", never as Low', () => {
    render(<ResultsList results={results} />)
    expect(screen.getByText('Unknown')).toHaveClass('level-Unknown')
    expect(screen.getByText('Value: no data')).toBeInTheDocument()
    expect(screen.queryByText('Low')).not.toBeInTheDocument()
  })
})
