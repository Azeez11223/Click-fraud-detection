import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { CampaignForm } from './CampaignForm'

describe('CampaignForm validation', () => {
  it('shows inline errors and blocks an empty campaign submission', async () => {
    const user = userEvent.setup()
    const onCreated = vi.fn()
    render(<CampaignForm onCreated={onCreated} onCancel={vi.fn()} />)

    await user.click(screen.getByRole('button', { name: 'Create campaign' }))

    expect(await screen.findByText('Campaign name is required')).toBeInTheDocument()
    expect(onCreated).not.toHaveBeenCalled()
  })

  it('validates cost inputs against the supported ranges', async () => {
    const user = userEvent.setup()
    render(<CampaignForm onCreated={vi.fn()} onCancel={vi.fn()} />)
    await user.type(screen.getByLabelText('Campaign name'), 'Search Launch')
    const rate = screen.getByLabelText(/Expected conversion rate/)
    await user.clear(rate)
    await user.type(rate, '1.5')
    await user.click(screen.getByRole('button', { name: 'Create campaign' }))
    expect(await screen.findByText('Rate must be between 0 and 1')).toBeInTheDocument()
  })

  it('rejects blank numeric inputs instead of silently converting them to zero', async () => {
    const user = userEvent.setup()
    render(<CampaignForm onCreated={vi.fn()} onCancel={vi.fn()} />)
    await user.type(screen.getByLabelText('Campaign name'), 'Search Launch')
    await user.clear(screen.getByLabelText('Cost per click ($)'))
    await user.click(screen.getByRole('button', { name: 'Create campaign' }))
    expect(await screen.findByText('Invalid input: expected number, received NaN')).toBeInTheDocument()
  })
})
