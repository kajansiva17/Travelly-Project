# Super Admin personal profile - 6 November 2026

Authority: the user's explicit 6 November Super Admin navigation/profile request. This scoped amendment retains the shared account, existing ADMIN membership, authentication, contact-verification/security workflows and twenty-table target. It does not replace missing historical contracts.

## UI boundary

The existing `/account?workspace=admin` route displays the compact personal profile in the authorized Admin shell. Navbar identity and sidebar Profile both use that route. Admin navbar identity is a link with avatar, full name and Super Admin label; there is no dropdown/chevron. Other workspace account menus are preserved. Sidebar Dashboard, Settings and Logout keep their existing destinations and behavior.

Admin Profile contains photo upload/change/remove, editable full name/mobile, read-only email and role, Save Changes and Cancel. Google linking, verification, documents and extra dashboard/logout navigation are absent from this profile. Existing security components remain under `/admin/settings`, and existing document management is preserved elsewhere. No duplicate profile route or role selector is introduced.

## PATCH /api/v1/users/me

- Existing authenticated, unrestricted account and currently approved ADMIN membership required. Target identity comes only from the existing session; there is no client user ID.
- Required fields: `version` (integer >= 1), `full_name` (trimmed, 1-150 characters, existing control-character validation), `phone_e164` (existing international/E.164 validation or null), `profile_image_url` (image data URL or null). Unknown fields are rejected. Email, roles, account status, credentials and verification timestamps cannot be supplied.
- Version must equal the locked current user version; mismatch returns `409 PROFILE_CHANGED`. Current account/auth version/session and Admin access are rechecked at mutation. Successful writes update existing users fields plus updated_by/updated_at/version, then return the existing allowlisted UserResponse.
- Unique-phone conflicts return `409 CONTACT_ALREADY_REGISTERED` with a phone field error, with the transaction rolled back.
- A changed number clears its prior phone verification. An ACTIVE account without verified email cannot change its number through this endpoint (`409 EMAIL_VERIFICATION_REQUIRED`), preserving the existing activation constraint. Existing email verification remains available in Settings. No verification or role approval is granted by editing.

## Existing photo column

No new table, column, migration, storage key, external image host or photo directory is introduced. `users.profile_image_url` stores a self-contained, metadata-free JPEG data URL for uploaded avatars. New uploads accept JPEG/PNG/WebP base64 data URLs only, at most 1 MiB decoded and 16 million pixels. Server decoding verifies the actual image format, strips metadata using a fresh RGB image, and reduces it to at most 256 x 256 before encoding. No uploaded SVG/HTML or arbitrary external/private document URL is accepted. An unchanged legacy image URL is retained; null removes the avatar. The bounded profile JSON request limit is 1,410,000 bytes; other API body limits remain unchanged.

Avatar data is returned only through the existing authenticated profile response. No public lookup by user ID, token persistence, password change, Google identity change or membership mutation is added. Images are not written into private-document or audit storage.
