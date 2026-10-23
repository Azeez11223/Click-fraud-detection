import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiFetch } from './client'

describe('apiFetch error handling', () => {
  afterEach(() => vi.unstubAllGlobals())

  it.each([
    [{ detail: 'Invalid email or password' }, 'Invalid email or password'],
    [{ error: { message: 'Rate limited' } }, 'Rate limited'],
  ])('parses the API error payload %j', async (body, expected) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status: 400 })))
    await expect(apiFetch('/example')).rejects.toMatchObject({ name: 'ApiError', message: expected, status: 400 })
  })

  it('normalizes a non-JSON error response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('nope', { status: 502 })))
    await expect(apiFetch('/example')).rejects.toMatchObject({
      name: 'ApiError', message: 'Request failed (502)', status: 502,
    } satisfies Partial<ApiError>)
  })
})
