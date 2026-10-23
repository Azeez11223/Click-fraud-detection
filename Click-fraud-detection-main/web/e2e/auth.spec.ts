import { expect, test } from '@playwright/test'

test('sign up, log in, and restore the session after refresh', async ({ page }) => {
  const user = { id: 73, name: 'Browser Tester', email: 'browser.tester@example.test' }
  let expireSession = false
  await page.route('**/healthz', (route) => route.fulfill({ json: { status: 'ok' } }))
  await page.route('**/auth/signup', (route) => route.fulfill({ json: { message: 'Account created', user_id: user.id } }))
  await page.route('**/auth/login', (route) => route.fulfill({ json: { access_token: 'playwright-session-token', token_type: 'bearer', user } }))
  await page.route('**/auth/me', (route) => expireSession
    ? route.fulfill({ status: 401, json: { detail: 'Session expired' } })
    : route.fulfill({ json: user }))

  await page.goto('/signup')
  await page.getByLabel('Full name').fill(user.name)
  await page.getByLabel('Email address').fill(user.email)
  await page.getByLabel('Password').fill('a-safe-test-password')
  await page.getByRole('button', { name: 'Create account' }).click()

  await expect(page).toHaveURL(/\/login$/)
  await page.getByLabel('Email address').fill(user.email)
  await page.getByLabel('Password').fill('a-safe-test-password')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('heading', { name: 'Operations dashboard' })).toBeVisible()
  await expect(page.getByRole('navigation', { name: 'Main navigation' })).toBeVisible()

  await page.reload()
  await expect(page.getByRole('heading', { name: 'Operations dashboard' })).toBeVisible()

  expireSession = true
  await page.reload()
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible()
  expect(await page.evaluate(() => sessionStorage.getItem('adshield_access_token'))).toBeNull()
})
