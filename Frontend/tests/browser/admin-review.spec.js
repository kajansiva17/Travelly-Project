import { test, expect } from '@playwright/test'

// Contract fixtures only inside tests; production UI always fetches real authorized records.
const now = '2026-10-26T06:00:00Z'
const uid = '12222222-2222-4222-8222-222222222222', rid = '32222222-2222-4222-8222-222222222222', did = '42222222-2222-4222-8222-222222222222'
async function setup(page, { admin = true, status = 'PENDING', fail = false } = {}) {
  const roles = [{ id: 'passenger', role_code: 'PASSENGER', approval_status: 'APPROVED' }]
  const user = { id: uid, full_name: 'Review Operator', display_name: null, public_user_reference: 'USR-0000000000000001', email: 'review@example.com', phone_e164: null, account_status: 'PENDING_VERIFICATION', email_verified_at: null, phone_verified_at: null, approved_roles: admin ? ['PASSENGER', 'ADMIN'] : ['PASSENGER'] }
  let application = { id: rid, role_code: 'OWNER', approval_status: status, requested_at: now, version: 1, approved_at: status === 'APPROVED' ? now : null, approved_by: null, rejection_reason: null, suspended_at: null, suspension_reason: null, updated_at: now, updated_by: null }
  let doc = { id: did, user_id: uid, vehicle_id: null, document_type: 'NIC', issuing_country: null, issue_date: null, expiry_date: null, status: 'UNDER_REVIEW', submitted_at: now, verified_at: null, rejection_reason: null, superseded_document_id: null, version: 2 }
  const mutations = [], files = []
  await page.route('**/api/v1/**', async route => {
    const request = route.request(), path = new URL(request.url()).pathname
    let body, code = 200
    if (path.endsWith('/auth/login')) body = { access_token: 'test-access', refresh_token: 'test-refresh', expires_in: 900 }
    else if (path.endsWith('/users/me')) body = user
    else if (path.endsWith('/users/me/roles')) body = { items: roles }
    else if (path === '/api/v1/admin/role-requests') {
      if (fail) { code = 503; body = { code: 'REVIEW_DEPENDENCY_UNAVAILABLE', message: 'Review is temporarily unavailable.' } }
      else body = { items: [{ ...application, applicant: { id: uid, full_name: 'Real Contract Applicant', public_user_reference: 'USR-0000000000000002' } }], page: 1, page_size: 20, total: 1, has_next: false }
    } else if (path.endsWith('/review')) {
      const value = request.postDataJSON(); mutations.push(value)
      if (path.includes('/documents/')) doc = { ...doc, status: value.decision, version: doc.version + 1, rejection_reason: value.reason }
      else application = { ...application, approval_status: value.decision, version: application.version + 1, rejection_reason: value.decision === 'REJECTED' ? value.reason : null, suspension_reason: value.decision === 'SUSPENDED' ? value.reason : null }
      body = application
    } else if (path.endsWith('/file')) {
      files.push(request.headers())
      return route.fulfill({ status: 200, contentType: 'image/png', body: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=', 'base64') })
    } else if (path === '/api/v1/admin/role-requests/' + rid) body = { application, applicant: { ...user, full_name: 'Real Contract Applicant' }, documents: [doc] }
    else { code = 404; body = { code: 'DOCUMENT_NOT_FOUND', message: 'Document not found.' } }
    return route.fulfill({ status: code, contentType: 'application/json', body: JSON.stringify(body) })
  })
  await page.goto('/login')
  await page.getByLabel('Email address', { exact: true }).fill('review@example.com')
  await page.getByLabel('Password', { exact: true }).fill('a private test passphrase')
  await page.getByRole('button', { name: 'Log in', exact: true }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('heading', { name: 'Hello, Review Operator.' })).toBeVisible()
  if (admin) {
    if (await page.getByRole('button', { name: 'Open navigation' }).isVisible()) await page.getByRole('button', { name: 'Open navigation' }).click()
    await page.getByRole('link', { name: 'Application review', exact: true }).click()
  }
  return { mutations, files }
}

test('anonymous and non-Admin route access never exposes a queue', async ({ page }) => {
  await page.goto('/admin/applications'); await expect(page).toHaveURL(/\/login$/)
  await setup(page, { admin: false })
  await page.evaluate(() => { history.pushState({}, '', '/admin/applications'); dispatchEvent(new PopStateEvent('popstate')) })
  await expect(page.getByRole('heading', { name: 'Review access denied' })).toBeVisible()
  await expect(page.getByText('Real Contract Applicant')).toHaveCount(0)
})

test('real queue layout, protected preview and footer remain usable', async ({ page }) => {
  const c = await setup(page)
  await expect(page.getByRole('heading', { name: 'Real Contract Applicant' })).toBeVisible()
  await page.getByRole('link', { name: 'Review application', exact: true }).click()
  await page.getByRole('button', { name: 'View private document' }).click()
  await expect(page.getByAltText('Private application evidence')).toBeVisible()
  expect(c.files[0].authorization).toBe('Bearer test-access')
  await page.locator('footer').scrollIntoViewIfNeeded(); await expect(page.locator('footer')).toBeInViewport()
  expect(await page.evaluate(() => document.scrollingElement.scrollWidth <= innerWidth)).toBe(true)
  expect(await page.locator('.site-header').evaluate(el => getComputedStyle(el).position)).toBe('sticky')
  await page.screenshot({ path: test.info().outputPath('review-detail.png'), fullPage: true })
})

test('reject requires a visible full reason and explicit confirmation', async ({ page }) => {
  const c = await setup(page)
  await page.getByRole('link', { name: 'Review application', exact: true }).click()
  await page.getByRole('button', { name: 'Reject Owner' }).click()
  await expect(page.getByRole('button', { name: 'Review confirmation' })).toBeDisabled()
  await page.getByLabel('Applicant-visible reason').fill('Please supply readable ownership evidence.')
  await page.getByRole('button', { name: 'Review confirmation' }).click()
  expect(c.mutations).toHaveLength(0)
  await page.getByRole('button', { name: 'Confirm decision' }).click()
  await expect(page.getByText('Decision saved.', { exact: false })).toBeVisible()
  expect(c.mutations).toEqual([{ decision: 'REJECTED', version: 1, reason: 'Please supply readable ownership evidence.' }])
  await expect(page.getByRole('button', { name: 'Approve Owner' })).toHaveCount(0)
})

test('Owner approval and approved-role suspension preserve independent actions', async ({ page }) => {
  const c = await setup(page)
  await page.getByRole('link', { name: 'Review application', exact: true }).click()
  await page.getByRole('button', { name: 'Approve Owner' }).click()
  await page.getByRole('button', { name: 'Review confirmation' }).click()
  await page.getByRole('button', { name: 'Confirm decision' }).click()
  await page.getByRole('button', { name: 'Suspend Owner' }).click()
  await page.getByLabel('Applicant-visible reason').fill('Authorization requires renewed review.')
  await page.getByRole('button', { name: 'Review confirmation' }).click()
  await page.getByRole('button', { name: 'Confirm decision' }).click()
  await expect(page.getByRole('button', { name: 'Suspend Owner' })).toHaveCount(0)
  expect(c.mutations.map(m => [m.decision, m.version])).toEqual([['APPROVED', 1], ['SUSPENDED', 2]])
})

test('document correction leaves a separate pending application', async ({ page }) => {
  const c = await setup(page)
  await page.getByRole('link', { name: 'Review application', exact: true }).click()
  await page.getByRole('button', { name: 'Request correction' }).click()
  await page.getByLabel('Applicant-visible reason').fill('Please upload both sides of your identity document.')
  await page.getByRole('button', { name: 'Review confirmation' }).click()
  await page.getByRole('button', { name: 'Confirm decision' }).click()
  await expect(page.getByText('NEEDS_CORRECTION · version 3')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Approve Owner' })).toBeVisible()
  expect(c.mutations[0].decision).toBe('NEEDS_CORRECTION')
})

test('dependency errors are distinct from empty queue', async ({ page }) => {
  await setup(page, { fail: true })
  await expect(page.getByText('Review is temporarily unavailable.')).toBeVisible()
  await expect(page.getByText('No pending applications', { exact: true })).toHaveCount(0)
})

test('version conflict and uncertain commit reload authoritative detail', async ({ page }) => {
  const c = await setup(page)
  await page.getByRole('link', { name: 'Review application', exact: true }).click()
  let reloads = 0
  page.on('request', r => { if (new URL(r.url()).pathname === '/api/v1/admin/role-requests/' + rid && r.method() === 'GET') reloads += 1 })
  await page.route('**/api/v1/admin/role-requests/*/review', route => route.fulfill({ status: 409, contentType: 'application/json', body: JSON.stringify({ code: 'VERSION_CONFLICT', message: 'This application has changed. Refresh before reviewing.' }) }))
  await page.getByRole('button', { name: 'Approve Owner' }).click()
  await page.getByRole('button', { name: 'Review confirmation' }).click()
  await page.getByRole('button', { name: 'Confirm decision' }).click()
  await expect(page.getByText('This application has changed. Refresh before reviewing.')).toBeVisible()
  expect(reloads).toBeGreaterThan(0); expect(c.mutations).toHaveLength(0)
})

test('unknown commit outcome refreshes without claiming success', async ({ page }) => {
  await setup(page)
  await page.getByRole('link', { name: 'Review application', exact: true }).click()
  await page.route('**/api/v1/admin/role-requests/*/review', route => route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ code: 'INTERNAL_ERROR', message: 'The decision outcome could not be confirmed. Refresh before retrying.' }) }))
  await page.getByRole('button', { name: 'Approve Owner' }).click()
  await page.getByRole('button', { name: 'Review confirmation' }).click()
  await page.getByRole('button', { name: 'Confirm decision' }).click()
  await expect(page.getByText('The decision outcome could not be confirmed. Refresh before retrying.')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Real Contract Applicant · OWNER' })).toBeVisible()
  await expect(page.getByText('Decision saved.', { exact: false })).toHaveCount(0)
})

test('revoked Admin clears private detail on the next attempted action', async ({ page }) => {
  await setup(page)
  await page.getByRole('link', { name: 'Review application', exact: true }).click()
  await page.route('**/api/v1/admin/role-requests/*/review', route => route.fulfill({ status: 403, contentType: 'application/json', body: JSON.stringify({ code: 'ADMIN_REQUIRED', message: 'Admin access is required.' }) }))
  await page.getByRole('button', { name: 'Approve Owner' }).click()
  await page.getByRole('button', { name: 'Review confirmation' }).click()
  await page.getByRole('button', { name: 'Confirm decision' }).click()
  await expect(page.getByRole('heading', { name: 'Review access denied' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'View private document' })).toHaveCount(0)
})

test('empty filtered queue has loading and empty states with bounded filters', async ({ page }) => {
  await setup(page)
  await expect(page.getByRole('heading', { name: 'Real Contract Applicant' })).toBeVisible()
  const queries = []
  await page.route('**/api/v1/admin/role-requests?*', async route => {
    const query = new URL(route.request().url()).searchParams
    queries.push(Object.fromEntries(query))
    await new Promise(resolve => setTimeout(resolve, 200))
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], page: 1, page_size: 20, total: 0, has_next: false }) })
  })
  for (const status of ['APPROVED', 'REJECTED', 'SUSPENDED', 'ALL']) {
    await page.getByLabel('Status', { exact: true }).selectOption(status)
    await expect(page.getByText('Loading authorized review data…')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'No applications match these filters' })).toBeVisible()
  }
  await page.getByLabel('Application type').selectOption('DRIVER')
  await expect(page.getByRole('heading', { name: 'No applications match these filters' })).toBeVisible()
  expect(queries.at(-1).role_code).toBe('DRIVER')
})

test('applicant uploads private evidence through existing profile without changing workspace', async ({ page }) => {
  await setup(page, { admin: false })
  const uploads = []
  await page.route('**/api/v1/documents**', route => {
    if (route.request().method() === 'POST') { uploads.push(route.request().headers()['content-type']); return route.fulfill({ status: 201, contentType: 'application/json', body: '{}' }) }
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], page: 1, page_size: 20, total: 0, has_next: false }) })
  })
  await page.evaluate(() => { history.pushState({}, '', '/account'); dispatchEvent(new PopStateEvent('popstate')) })
  await expect(page.getByRole('heading', { name: 'Your private application documents' })).toBeVisible()
  await page.getByLabel('Document file', { exact: false }).setInputFiles({ name: 'identity.png', mimeType: 'image/png', buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=', 'base64') })
  await page.getByRole('button', { name: 'Submit private document', exact: true }).click()
  await expect(page.getByText('Your private document was submitted for review.', { exact: false })).toBeVisible()
  expect(uploads[0]).toContain('multipart/form-data; boundary=')
})
