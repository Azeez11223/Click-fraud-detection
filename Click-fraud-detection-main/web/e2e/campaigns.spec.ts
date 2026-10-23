import { expect, test } from '@playwright/test'

test('create a campaign, open it, and update its block threshold', async ({ page }) => {
  const user = { id: 41, name: 'Campaign Tester', email: 'campaign.tester@example.test' }
  let activeThreshold = 0.7
  let thresholdSaved = false
  let campaignCreated = false
  let campaign = {
    id: 42, user_id: user.id, name: 'Spring Search', ad_type: 'Search', platform: 'Google', purpose: 'Traffic',
    status: 'Active', created_at: '2026-10-21 10:00:00', cpc: 0.5, avg_conversion_value: 25,
    expected_conversion_rate: 0.02, block_threshold: activeThreshold, click_count: 0, fraud_count: 0, valid_count: 0, suspicious_count: 0,
  }
  await page.addInitScript(({ currentUser }) => {
    sessionStorage.setItem('adshield_access_token', 'campaign-e2e-token')
    sessionStorage.setItem('adshield_user', JSON.stringify(currentUser))
  }, { currentUser: user })
  await page.route('**/auth/me', (route) => route.fulfill({ json: user }))
  await page.route('http://localhost:8000/campaigns**', async (route) => {
    const url = new URL(route.request().url())
    const method = route.request().method()
    if (url.pathname === '/campaigns' && method === 'GET') return route.fulfill({ json: campaignCreated ? [campaign] : [] })
    if (url.pathname === '/campaigns' && method === 'POST') {
      const body = route.request().postDataJSON() as { name: string; ad_type: string; platform: string; purpose: string; cpc: number; avg_conversion_value: number; expected_conversion_rate: number }
      campaign = { ...campaign, ...body }
      campaignCreated = true
      return route.fulfill({ json: { message: 'Campaign created', campaign_id: campaign.id, api_key: 'one-time-campaign-key', note: 'Save this API key.' } })
    }
    if (url.pathname === '/campaigns/42' && method === 'GET') return route.fulfill({ json: campaign })
    if (url.pathname === '/campaigns/42/stats') return route.fulfill({ json: { total: 0, fraud: 0, suspicious: 0, valid: 0, fraud_rate: 0 } })
    if (url.pathname === '/campaigns/42/alerts') return route.fulfill({ json: [] })
    if (url.pathname === '/campaigns/42/threshold-analysis') return route.fulfill({ json: {
      recommended_block_threshold: 0.66, active_block_threshold: activeThreshold,
      analysis: { threshold: Number(url.searchParams.get('threshold') ?? activeThreshold), estimated_wasted_spend_saved: 0, estimated_legitimate_conversions_lost: 0, estimated_conversion_value_lost: 0, sample_size: 0, labelled_fraud_count: 0, labelled_legitimate_count: 0 },
      estimate_notice: 'Historical classification labels and scores are proxies, not verified outcomes.',
    } })
    if (url.pathname === '/campaigns/42/block-threshold' && method === 'PATCH') {
      activeThreshold = (route.request().postDataJSON() as { block_threshold: number }).block_threshold
      thresholdSaved = true
      return route.fulfill({ json: { block_threshold: activeThreshold } })
    }
    return route.fulfill({ status: 404, json: { detail: `Unhandled ${method} ${url.pathname}` } })
  })

  await page.goto('/campaigns')
  await page.getByRole('button', { name: 'New campaign' }).first().click()
  await page.getByLabel('Campaign name').fill(campaign.name)
  await page.getByRole('button', { name: 'Create campaign' }).click()
  await expect(page).toHaveURL(/\/campaigns\/42$/)
  await expect(page.getByRole('heading', { name: 'Spring Search' })).toBeVisible()

  await page.getByRole('tab', { name: 'Economics & Threshold' }).click()
  const slider = page.getByRole('slider', { name: 'Preview block sensitivity' })
  await expect(slider).toHaveValue('0.7')
  await slider.press('ArrowRight')
  await expect(slider).toHaveValue('0.71')
  await page.getByRole('button', { name: 'Save block threshold' }).click()
  await expect.poll(() => thresholdSaved).toBe(true)
  await expect(page.getByText('Active:', { exact: false })).toContainText('0.71')
})
