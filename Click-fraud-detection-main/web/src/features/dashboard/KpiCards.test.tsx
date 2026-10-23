import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { KpiRiskBadge } from './KpiCards'

describe('fraud risk badge thresholds', () => {
  it.each([[0, 'low'], [19.9, 'low'], [20, 'medium'], [49.9, 'medium'], [50, 'high'], [100, 'high']] as const)(
    'classifies a %s%% rate as %s risk', (rate, level) => {
      const { container } = render(<KpiRiskBadge rate={rate} />)
      expect(screen.getByLabelText(`${level} risk`)).toBeInTheDocument()
      expect(container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true')
    },
  )
})
