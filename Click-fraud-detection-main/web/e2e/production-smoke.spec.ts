import { expect, test } from '@playwright/test'

const user={id:18,name:'Smoke Tester',email:'smoke@example.test'}

test('login form is keyboard reachable and labelled',async({page})=>{
  await page.route('**/healthz',route=>route.fulfill({json:{status:'ok'}}))
  await page.goto('/login')
  await expect(page.getByRole('heading',{name:'Welcome back'})).toBeVisible()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link',{name:'AdShield'})).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByLabel('Email address')).toBeFocused()
  await expect(page.getByLabel('Password')).toBeAttached()
})

test('authenticated dashboard loads without a navigation error',async({page})=>{
  await page.addInitScript(({currentUser})=>{
    sessionStorage.setItem('adshield_access_token','smoke-test-token')
    sessionStorage.setItem('adshield_user',JSON.stringify(currentUser))
  },{currentUser:user})
  await page.route('**/auth/me',route=>route.fulfill({json:user}))
  await page.route('**/stats',route=>route.fulfill({json:{total:0,fraud:0,review:0,legit:0,fraud_rate:0}}))
  await page.route('**/clicks?limit=200',route=>route.fulfill({json:[]}))
  await page.route('**/alerts',route=>route.fulfill({json:[]}))
  await page.route('**/campaigns?limit=500',route=>route.fulfill({json:[]}))
  await page.goto('/dashboard')
  await expect(page.getByRole('heading',{name:'Operations dashboard'})).toBeVisible()
  await expect(page.getByText('Create your first campaign')).toBeVisible()
  await expect(page.getByRole('navigation',{name:'Main navigation'})).toBeVisible()
})
