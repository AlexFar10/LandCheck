import { describe, expect, it } from 'vitest'
import { BASEMAP_STYLE, PILOT_CENTER } from './basemap'
import { displayValue } from './format'

describe('basemap', () => {
  it('is centred on Pechea in [lon, lat] order', () => {
    const [lon, lat] = PILOT_CENTER
    expect(lon).toBeCloseTo(27.8, 1)
    expect(lat).toBeCloseTo(45.63, 1)
  })

  it('every basemap source has an attribution', () => {
    for (const source of Object.values(BASEMAP_STYLE.sources)) {
      expect('attribution' in source && source.attribution).toMatch(/OpenStreetMap/)
    }
  })
})

describe('displayValue', () => {
  it('shows null and undefined as "Not available"', () => {
    expect(displayValue(null)).toBe('Not available')
    expect(displayValue(undefined)).toBe('Not available')
  })

  it('keeps real zeros', () => {
    expect(displayValue(0)).toBe('0')
  })
})
