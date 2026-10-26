import { test, expect } from '@playwright/test'

const uid = 'b59140a1-f9fb-4a37-9717-f97fc3e64f73'
const types = ['NIC', 'PASSPORT', 'DRIVING_LICENCE', 'VEHICLE_REGISTRATION', 'OWNER_AUTHORISATION']
// Isolated component captures omit unrelated sticky navigation; layout checks run unmodified.
const captureStyle = '.site-header, .site-header *, .skip-link { visibility: hidden !important; }'
const png = { name: 'evidence.png', mimeType: 'image/png', buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=', 'base64') }

async function setup(page) {
  const uploads = []
  const user = { id: uid, full_name: 'Document Applicant', public_user_reference: 'USR-1234567890123456', email: 'applicant@example.com', account_status: 'PENDING_VERIFICATION', approved_roles: ['PASSENGER'] }
  await page.route('**/api/v1/**', async route => {
    const request = route.request(), path = new URL(request.url()).pathname
    let body
    if (path.endsWith('/auth/login')) body = { access_token: 'test-access', refresh_token: 'test-refresh', expires_in: 900 }
    else if (path.endsWith('/users/me')) body = user
    else if (path.endsWith('/users/me/roles')) body = { items: [{ role_code: 'PASSENGER', approval_status: 'APPROVED' }] }
    else if (path === '/api/v1/documents' && request.method() === 'POST') { uploads.push(request.postDataBuffer().toString()); body = { id: 'submitted-document', status: 'SUBMITTED' } }
    else if (path === '/api/v1/documents') body = { items: [], page: 1, page_size: 20, total: 0, has_next: false }
    else return route.fulfill({ status: 404, json: { message: 'Unexpected test request.' } })
    await route.fulfill({ status: request.method() === 'POST' && path.endsWith('/documents') ? 201 : 200, json: body })
  })
  await page.goto('/login')
  await page.getByLabel('Email address', { exact: true }).fill('applicant@example.com')
  await page.getByLabel('Password', { exact: true }).fill('a private test passphrase')
  await page.getByRole('button', { name: 'Log in', exact: true }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  // Client-side navigation preserves the memory-only session.
  await page.evaluate(() => { history.pushState({}, '', '/account'); dispatchEvent(new PopStateEvent('popstate')) })
  await expect(page.getByRole('heading', { name: 'Your private application documents' })).toBeVisible()
  return { uploads, form: page.getByRole('form', { name: 'Private document upload' }) }
}

for (const ownership of ['SELF', 'INDIVIDUAL', 'COMPANY']) {
  test(`all document types, ownership ${ownership}: guidance, fields and responsive layout`, async ({ page }) => {
    const { form } = await setup(page)
    await page.getByLabel('Whose name is on the vehicle registration?').selectOption(ownership)
    const guide = page.locator('.ownership-case')
    await expect(guide).toContainText(ownership === 'SELF' ? 'showing you as the registered owner' : ownership === 'COMPANY' ? 'no company account is needed' : 'authorization from that registered individual')
    await expect(page.locator('.vehicle-registration-note')).toContainText('does not replace its registration')
    for (const type of types) {
      await form.getByLabel('Document type').selectOption(type)
      await expect(form.locator('.document-requirement')).toHaveText(type === 'OWNER_AUTHORISATION' && ownership === 'SELF' ? 'Optional' : 'Required for your case')
      await expect(form.locator('[name="number"]')).toHaveAttribute('aria-describedby', 'upload-number-hint')
      await expect(form.locator('[name="number"]')).not.toHaveAttribute('required')
      await expect(form.getByLabel('Document file')).toHaveAttribute('required', '')
      if (type === 'OWNER_AUTHORISATION') await expect(form.getByLabel('Issuing country')).toHaveCount(0)
      else {
        await expect(form.getByLabel('Issuing country')).toHaveValue(type === 'DRIVING_LICENCE' ? 'LK' : '')
        await expect(form.getByLabel('Issuing country').getByRole('option', { name: 'Sri Lanka', exact: true })).toHaveCount(1)
      }
      if (['PASSPORT', 'DRIVING_LICENCE'].includes(type)) {
        await expect(form.getByLabel('Expiry date', { exact: false })).toBeVisible()
        await expect(form.locator('[name="expiry_date"]')).not.toHaveAttribute('required')
      } else {
        await expect(form.locator('[name="expiry_date"]')).toHaveCount(0)
        await form.getByRole('checkbox').check()
        await expect(form.locator('[name="expiry_date"]')).toBeVisible()
        await form.getByRole('checkbox').uncheck()
        await expect(form.locator('[name="expiry_date"]')).toHaveCount(0)
      }
      await form.getByLabel('Document file').scrollIntoViewIfNeeded()
      expect(await page.evaluate(() => document.scrollingElement.scrollWidth <= innerWidth)).toBe(true)
      for (const control of await form.locator('input, select, button').all()) {
        const box = await control.boundingBox()
        expect(box.x).toBeGreaterThanOrEqual(0)
        expect(box.x + box.width).toBeLessThanOrEqual(page.viewportSize().width + 1)
      }
      await form.screenshot({ path: test.info().outputPath(`${ownership}-${type}.png`), style: captureStyle })
    }
    await page.locator('.document-checklist').screenshot({ path: test.info().outputPath(`${ownership}-checklist.png`), style: captureStyle })
  })
}

for (const type of types) test(`${type}: submit without unprinted numbers or dates`, async ({ page }) => {
  const { form, uploads } = await setup(page)
  await form.getByLabel('Document type').selectOption(type)
  await form.getByLabel('Document file').setInputFiles(png)
  await form.getByRole('button', { name: 'Submit private document' }).click()
  await expect(form.getByText('Your private document was submitted for review.', { exact: false })).toBeVisible()
  expect(uploads).toHaveLength(1)
  const payload = uploads[0]
  expect(payload).toContain(`name="document_type"\r\n\r\n${type}`)
  expect(payload).not.toContain('name="number"')
  expect(payload).not.toContain('name="issue_date"')
  expect(payload).not.toContain('name="expiry_date"')
  expect(payload).not.toContain('ownership')
  expect(payload.includes('name="issuing_country"')).toBe(type === 'DRIVING_LICENCE')
})

test('date order and file errors are inline; country names send ISO codes; changing type clears stale metadata and file', async ({ page }) => {
  const { form, uploads } = await setup(page)
  await form.getByRole('button', { name: 'Submit private document' }).click()
  await expect(form.getByText('Choose a non-empty PDF, JPG or PNG file.')).toBeVisible()
  await expect(form.getByLabel('Document file')).toBeFocused()
  await form.getByLabel('Document type').selectOption('PASSPORT')
  await form.getByLabel('Issuing country').selectOption({ label: 'United Kingdom' })
  await form.getByLabel('Issue date').fill('2026-10-26')
  await form.getByLabel('Expiry date').fill('2026-10-25')
  await form.getByLabel('Document file').setInputFiles(png)
  await form.getByRole('button', { name: 'Submit private document' }).click()
  await expect(form.getByText('Expiry date must be on or after the issue date.')).toBeVisible()
  await expect(form.getByLabel('Expiry date')).toBeFocused()
  expect(uploads).toHaveLength(0)
  await form.getByLabel('Expiry date').fill('2030-10-26')
  await form.getByRole('button', { name: 'Submit private document' }).click()
  await expect(form.getByText('Your private document was submitted for review.', { exact: false })).toBeVisible()
  expect(uploads[0]).toContain('name="issuing_country"\r\n\r\nGB')
  await form.getByLabel('Document type').selectOption('PASSPORT')
  await form.getByLabel('Passport number').fill('PRIVATE-123')
  await form.getByLabel('Document file').setInputFiles(png)
  await form.getByLabel('Document type').selectOption('OWNER_AUTHORISATION')
  await expect(form.getByLabel('Authorization reference number')).toHaveValue('')
  await expect(form.getByLabel('Document file')).toHaveValue('')
  await expect(form.getByLabel('Issuing country')).toHaveCount(0)
})

test('invalid type, oversize file and server validation preserve editable input', async ({ page }) => {
  const { form, uploads } = await setup(page)
  await form.getByLabel('Document file').setInputFiles({ name: 'file.svg', mimeType: 'image/svg+xml', buffer: Buffer.from('<svg/>') })
  await form.getByRole('button', { name: 'Submit private document' }).click()
  await expect(form.getByText('Choose a PDF, JPG or PNG file with a matching file extension.')).toBeVisible()
  await form.getByLabel('Document file').setInputFiles({ name: 'large.pdf', mimeType: 'application/pdf', buffer: Buffer.alloc(10485761) })
  await form.getByRole('button', { name: 'Submit private document' }).click()
  await expect(form.getByText('Choose a file no larger than 10 MiB (10,485,760 bytes).')).toBeVisible()
  expect(uploads).toHaveLength(0)
  await form.getByLabel('Identity card number').fill('KEEP-123')
  await form.getByLabel('Document file').setInputFiles(png)
  await page.route('**/api/v1/documents', route => route.fulfill({ status: 422, json: { message: 'Check the highlighted fields.', field_errors: [{ field: 'number', code: 'invalid_value', message: 'Enter 1–100 characters, or leave this optional field blank.' }] } }))
  await form.getByRole('button', { name: 'Submit private document' }).click()
  await expect(form.getByText('Enter 1–100 characters, or leave this optional field blank.')).toBeVisible()
  await expect(form.getByLabel('Identity card number')).toHaveValue('KEEP-123')
  await expect(form.getByLabel('Identity card number')).toBeFocused()
  await expect(form.getByLabel('Identity card number')).toHaveAttribute('aria-invalid', 'true')
})
