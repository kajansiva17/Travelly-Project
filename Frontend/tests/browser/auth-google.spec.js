import { test, expect } from '@playwright/test'
import { translate } from '../../src/i18n/language.js'

async function setup(page, { mode = 'completion', authoritative = true } = {}) {
  const requests = []
  const user = { id: 'd59140a1-f9fb-4a37-9717-f97fc3e64f73', full_name: 'Google Test Passenger', email: 'member@example.com', account_status: 'ACTIVE', email_verified_at: '2026-10-26T01:00:00Z', approved_roles: ['PASSENGER'] }
  await page.route('https://accounts.google.com/gsi/client', route => route.fulfill({ contentType: 'application/javascript', body: `window.google={accounts:{id:{initialize(c){this.config=c},renderButton(host){const b=document.createElement('button');b.textContent='Continue with Google';b.style.cssText='width:100%;min-height:44px';b.onclick=()=>this.config.callback({credential:'test-google-credential'});host.appendChild(b)}}}};` }))
  await page.route('**/api/v1/**', async route => {
    const req = route.request(), path = new URL(req.url()).pathname
    const data = req.method() === 'POST' ? req.postDataJSON() : null
    requests.push({ path, data })
    let result, code = 200
    if (path.endsWith('/challenge')) result = { client_id: 'test-client', nonce: 'n'.repeat(43), challenge: 'c'.repeat(43) }
    else if (path === '/api/v1/auth/google') {
      if (mode === 'invalid') { code = 401; result = { message: 'Google sign-in could not be verified. Try again.' } }
      else result = mode === 'conflict' ? { status: 'link_required', message: 'A Travelly account already uses this email. Sign in using its existing method, then connect Google in Profile.' } : { status: 'completion_required', ticket: 't'.repeat(43), email: 'new@example.com', full_name: 'New Google Passenger' }
    } else if (path === '/api/v1/auth/google/complete') result = authoritative ? { access_token: 'test-access', refresh_token: 'test-refresh' } : { status: 'verification_required', verification_ticket: 'v'.repeat(43), email_delivery: 'captured', message: 'Development email captured locally. No message was sent to an inbox.' }
    else if (path === '/api/v1/auth/login') result = { access_token: 'test-access', refresh_token: 'test-refresh' }
    else if (path === '/api/v1/users/me') result = user
    else if (path === '/api/v1/users/me/roles') result = { items: [{ role_code: 'PASSENGER', approval_status: 'APPROVED' }] }
    else if (path === '/api/v1/users/me/auth-methods') result = { password: true, google: false, email_verified: true }
    else if (path === '/api/v1/users/me/google') result = { message: 'Google is connected to this same Travelly account. Your roles and records are unchanged.' }
    else if (path === '/api/v1/documents') result = { items: [], page: 1, has_next: false }
    else { code = 404; result = { message: 'Unavailable test endpoint.' } }
    return route.fulfill({ status: code, json: result })
  })
  return requests
}

for (const start of ['/login', '/register']) test(`unconfigured Google on ${start} is disabled while email/password remains usable`, async ({ page }) => {
  const requests = await setup(page)
  let googleLibraryRequests = 0
  page.on('request', request => { if (request.url() === 'https://accounts.google.com/gsi/client') googleLibraryRequests++ })
  await page.route('**/api/v1/auth/google/challenge', route => route.fulfill({ status: 503, json: { code: 'GOOGLE_NOT_CONFIGURED', message: 'Google sign-in is not configured yet. Use email and password for now.' } }))
  await page.route('**/api/v1/auth/register', route => route.fulfill({ status: 201, json: { status: 'verification_required', verification_ticket: 'v'.repeat(43), email_delivery: 'captured', message: 'Development email captured locally.' } }))
  for (const width of [360, 768, 1366]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto(start)
    const button = page.getByRole('button', { name: 'Continue with Google', exact: true })
    await expect(button).toBeVisible()
    await expect(button).toBeDisabled()
    await expect(button).toHaveAccessibleDescription('Google sign-in will be available soon.')
    await expect(button.locator('svg')).toHaveAttribute('aria-hidden', 'true')
    await expect(page.getByText('Google sign-in is not configured yet.', { exact: false })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Retry Google sign-in' })).toHaveCount(0)
    await button.focus()
    await expect(button).not.toBeFocused()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.locator('.google-sign-in').screenshot({ path: test.info().outputPath(`google-unavailable-${width}.png`) })
  }
  expect(googleLibraryRequests).toBe(0)
  expect(requests.filter(r => r.path === '/api/v1/auth/google')).toHaveLength(0)
  await page.getByLabel('Email address', { exact: true }).fill('member@example.com')
  await page.getByLabel('Password', { exact: true }).fill('TravellyStrong1!')
  if(await page.getByLabel('Confirm password',{exact:true}).isVisible())await page.getByLabel('Confirm password',{exact:true}).fill('TravellyStrong1!')
  if (start === '/register') {
    await page.getByLabel('Full name', { exact: true }).fill('Test Passenger')
    await page.getByLabel('Mobile number', { exact: true }).fill('771234567')
    await page.locator('[name="accept_terms"]').check()
  }
  const submit = page.getByRole('button', { name: start === '/register' ? 'Create account' : 'Log in', exact: true })
  await expect(submit).toBeEnabled()
  await submit.focus()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(start === '/register' ? /\/check-email$/ : /\/dashboard$/)
})

test('temporary Google failure remains retryable', async ({ page }) => {
  await setup(page)
  let attempts = 0
  await page.route('**/api/v1/auth/google/challenge', route => route.fulfill(++attempts === 1
    ? { status: 503, json: { code: 'GOOGLE_UNAVAILABLE', message: 'Google sign-in is temporarily unavailable. Please try again.' } }
    : { json: { client_id: 'test-client', nonce: 'n'.repeat(43), challenge: 'c'.repeat(43) } }))
  await page.goto('/login')
  await expect(page.getByText('Google sign-in is temporarily unavailable. Please try again.')).toBeVisible()
  await expect(page.getByText('Google sign-in will be available soon.')).toHaveCount(0)
  await page.getByRole('button', { name: 'Retry Google sign-in' }).click()
  await expect(page.getByRole('button', { name: 'Continue with Google', exact: true })).toBeEnabled()
  await expect(page.getByRole('button', { name: 'Retry Google sign-in' })).toHaveCount(0)
})

for (const start of ['/login', '/register']) test(`Google on ${start} requires completion and terms before account creation`, async ({ page }) => {
  const requests = await setup(page)
  await page.goto(start)
  await page.getByRole('button', { name: 'Continue with Google', exact: true }).focus()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/google-complete$/)
  expect(requests.filter(r => r.path.endsWith('/google/complete'))).toHaveLength(0)
  await page.getByRole('button', { name: 'Create Passenger account' }).click()
  await expect(page.getByText('Enter your mobile number.')).toBeVisible()
  await page.getByLabel('Mobile number', { exact: true }).fill('771234567')
  await page.getByRole('button', { name: 'Create Passenger account' }).click()
  await expect(page.getByText('Agree to the Terms and Privacy Policy to continue.')).toBeVisible()
  await page.locator('[name="accept_terms"]').check()
  await page.screenshot({ path: test.info().outputPath('google-completion.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('button', { name: 'Create Passenger account' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  const body = requests.find(r => r.path.endsWith('/google/complete')).data
  expect(body.phone_e164).toBe('+94771234567'); expect(body.accept_terms).toBe(true)
  expect(body).not.toHaveProperty('email'); expect(body).not.toHaveProperty('role_code')
})

test('third-party Google email requires Travelly verification', async ({ page }) => {
  await setup(page, { authoritative: false })
  await page.goto('/login'); await page.getByRole('button', { name: 'Continue with Google', exact: true }).click()
  await page.getByLabel('Mobile number', { exact: true }).fill('771234567')
  await page.locator('[name="accept_terms"]').check()
  await page.getByRole('button', { name: 'Create Passenger account' }).click()
  await expect(page).toHaveURL(/\/check-email$/)
  await expect(page.getByText('No message was sent to an inbox.', { exact: false })).toBeVisible()
})

test('matching email never creates or links an account; invalid Google token shows an error', async ({ page }) => {
  const requests = await setup(page, { mode: 'conflict' })
  await page.goto('/login'); await page.getByRole('button', { name: 'Continue with Google', exact: true }).click()
  await expect(page.getByText('then connect Google in Profile.', { exact: false })).toBeVisible()
  await expect(page).toHaveURL(/\/login$/)
  expect(requests.filter(r => r.path.endsWith('/google/complete') || r.path === '/api/v1/users/me/google')).toHaveLength(0)
  await page.route('**/api/v1/auth/google', route => route.fulfill({ status: 401, json: { message: 'Google sign-in could not be verified. Try again.' } }))
  await page.getByRole('button', { name: 'Continue with Google', exact: true }).click()
  await expect(page.getByText('Google sign-in could not be verified. Try again.')).toBeVisible()
})

test('Profile linking needs current method and explicit confirmation', async ({ page }) => {
  const requests = await setup(page)
  await page.goto('/login')
  await page.getByLabel('Email address', { exact: true }).fill('member@example.com')
  await page.getByLabel('Password', { exact: true }).fill('existing password')
  await page.getByRole('button', { name: 'Log in', exact: true }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await page.evaluate(() => { history.pushState({}, '', '/account'); dispatchEvent(new PopStateEvent('popstate')) })
  await expect(page.getByLabel('Current password', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Continue with Google', exact: true })).toHaveCount(0)
  await page.getByLabel('Current password', { exact: true }).fill('existing password')
  await page.getByLabel('I confirm that I want to connect my Google sign-in to this account.').check()
  await page.getByRole('button', { name: 'Continue with Google', exact: true }).click()
  await expect(page.getByText('Google: Connected to this Travelly account')).toBeVisible()
  const link = requests.find(r => r.path === '/api/v1/users/me/google')
  expect(link.data.confirm).toBe(true); expect(link.data.current_password).toBe('existing password')
})

for(const code of ['ta','si']) test(`${code} Google library failure retains its icon, translated retry and entered form values`,async({page})=>{
  await page.addInitScript(code=>localStorage.setItem('travelly-language',code),code)
  await setup(page)
  await page.route('https://accounts.google.com/gsi/client',route=>route.abort('failed'))
  await page.goto('/login')
  const message='Google sign-in could not load. Try again or use email and password.'
  await expect(page.locator('.google-sign-in [role=status]')).toHaveText(translate(message,code))
  await expect(page.locator('.google-button-icon')).toBeVisible()
  await page.locator('#identifier').fill('retained@example.com');await page.locator('#password').fill('retained-password')
  await page.unroute('https://accounts.google.com/gsi/client')
  await page.route('https://accounts.google.com/gsi/client',route=>route.fulfill({contentType:'application/javascript',body:`window.google={accounts:{id:{initialize(c){this.config=c},renderButton(host,options){window.gisLocale=options.locale;const b=document.createElement('button');b.textContent='Continue with Google';host.appendChild(b)}}}}`}))
  await page.getByRole('button',{name:translate('Retry Google sign-in',code)}).click()
  await expect(page.getByRole('button',{name:'Continue with Google',exact:true})).toBeEnabled()
  await expect.poll(()=>page.evaluate(()=>window.gisLocale)).toBe(code)
  await expect(page.locator('#identifier')).toHaveValue('retained@example.com')
  await expect(page.locator('#password')).toHaveValue('retained-password')
})

test('repeated provider callbacks submit a credential once',async({page})=>{
  const requests=await setup(page)
  await page.goto('/login');await expect(page.getByRole('button',{name:'Continue with Google',exact:true})).toBeEnabled()
  await page.evaluate(()=>{
    const callback=window.google.accounts.id.config.callback
    callback({credential:'test-google-credential'});callback({credential:'test-google-credential'})
  })
  await expect(page).toHaveURL(/\/google-complete$/)
  expect(requests.filter(r=>r.path==='/api/v1/auth/google')).toHaveLength(1)
})

test('Google receives only the public origin and leaving auth restores no-referrer',async({page})=>{
  await setup(page)
  let googleReferrer
  await page.route('https://accounts.google.com/gsi/referrer-fixture',async route=>{
    googleReferrer=(await route.request().allHeaders()).referer
    await route.fulfill({contentType:'text/html',body:'<!doctype html><title>Anonymous policy fixture</title>'})
  })
  await page.route('https://accounts.google.com/gsi/client',route=>route.fulfill({contentType:'application/javascript',body:`window.google={accounts:{id:{initialize(){},renderButton(host){window.googleHostWidth=host.getBoundingClientRect().width;const b=document.createElement('button');b.textContent='Continue with Google';host.appendChild(b);const frame=document.createElement('iframe');frame.src='https://accounts.google.com/gsi/referrer-fixture';host.appendChild(frame)}}}}`}))
  await page.goto('/login?journey=OWNER&private_fixture=must-not-leak#private-fragment')
  await expect.poll(()=>googleReferrer).toBe(new URL(page.url()).origin+'/')
  expect(await page.evaluate(()=>window.googleHostWidth)).toBeGreaterThan(0)
  expect(googleReferrer).not.toContain('private_fixture')
  expect(googleReferrer).not.toContain('/login')
  await expect(page.locator('meta[name="referrer"]')).toHaveAttribute('content','strict-origin')
  await page.evaluate(()=>{history.pushState({},'','/');dispatchEvent(new PopStateEvent('popstate'))})
  await expect(page.locator('meta[name="referrer"]')).toHaveAttribute('content','no-referrer')
})
