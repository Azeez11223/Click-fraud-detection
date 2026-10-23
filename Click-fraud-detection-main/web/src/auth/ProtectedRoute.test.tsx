import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AuthProvider } from './AuthProvider'
import { ProtectedRoute } from './ProtectedRoute'

describe('ProtectedRoute', () => {
  it('redirects an unauthenticated visitor to login', async () => {
    render(<AuthProvider><MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route element={<ProtectedRoute />}><Route path="/dashboard" element={<p>Private dashboard</p>} /></Route>
        <Route path="/login" element={<p>Login screen</p>} />
      </Routes>
    </MemoryRouter></AuthProvider>)

    expect(await screen.findByText('Login screen')).toBeInTheDocument()
    expect(screen.queryByText('Private dashboard')).not.toBeInTheDocument()
  })
})
