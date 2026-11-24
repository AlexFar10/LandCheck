import { afterEach, describe, expect, it, vi } from 'vitest'
import { API_UNREACHABLE, ApiError, getHealth, getLayers } from './api'

function mockFetch(status: number, body: unknown) {
  const fetchMock = vi.fn(
    async (_input: RequestInfo | URL) => new Response(JSON.stringify(body), { status }),
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('api', () => {
  it('calls the same-origin Section 12 paths', async () => {
    const fetchMock = mockFetch(200, { layers: [] })
    await getLayers()
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/layers')
    mockFetch(200, { status: 'ok' })
    await expect(getHealth()).resolves.toEqual({ status: 'ok' })
  })

  it('throws the standard error object', async () => {
    mockFetch(503, {
      error: { code: 'DATASET_UNAVAILABLE', message: 'The dataset is not available.', details: {} },
    })
    const error = await getLayers().catch((err: unknown) => err)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 503, code: 'DATASET_UNAVAILABLE' })
  })

  it('reports the API as unreachable when the dev proxy returns a bare 502', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('', { status: 502 })))
    await expect(getLayers()).rejects.toMatchObject({ status: 502, code: API_UNREACHABLE })
  })

  it('reports the API as unreachable on a network error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('Failed to fetch')
      }),
    )
    const error = await getLayers().catch((err: unknown) => err)
    expect(error).toMatchObject({ status: 0, code: API_UNREACHABLE })
    expect((error as Error).message).toMatch(/Cannot reach the Land Check API/)
  })

  it('fails loudly on other non-JSON errors', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('oops', { status: 500 })))
    await expect(getHealth()).rejects.toMatchObject({ status: 500, code: 'HTTP_ERROR' })
  })
})
