import { t } from '../../i18n/language.js'
import React, { useEffect, useState } from 'react'
import { api } from '../../services/api'
import { ErrorNotice } from '../../components/components'
import { Chip, FormField, FormGrid, Input } from '../../components/ui'
import { useWorkspace } from '../../context/workspaceContext'

/* Profile details form. Uses the existing PATCH /users/me request (same body as the admin profile page).
   The Save button is rendered by the caller in the footer: <button type="submit" form="profile-details-form">. */
export const PROFILE_FORM_ID = 'profile-details-form'
const draftFor = user => ({ full_name: user.full_name || '', phone_e164: user.phone_e164 || '' })

export default function ProfileDetails({ user, onState }) {
  const workspace = useWorkspace()
  const [draft, setDraft] = useState(() => draftFor(user)), [busy, setBusy] = useState(false), [error, setError] = useState(null), [message, setMessage] = useState('')
  useEffect(() => { setDraft(draftFor(user)) }, [user])
  const changed = JSON.stringify(draft) !== JSON.stringify(draftFor(user))
  useEffect(() => { onState?.({ busy, changed, message }) }, [busy, changed, message])
  async function save(event) {
    event.preventDefault()
    if (busy || !changed) return
    setBusy(true); setError(null); setMessage('')
    try {
      const result = await api('/users/me', { method: 'PATCH', body: JSON.stringify({ full_name: draft.full_name.trim(), phone_e164: draft.phone_e164.trim() || null, profile_image_url: user.profile_image_url || null, version: user.version }) })
      workspace.updateProfile(result); setMessage('Your profile has been updated.')
    } catch (err) { setError(err) } finally { setBusy(false) }
  }
  const roles = (user.approved_roles || []).filter(code => code !== 'PASSENGER')
  return <form id={PROFILE_FORM_ID} className="profile-details" onSubmit={save} aria-label={t("Personal profile")}>
    <ErrorNotice error={error}/>{error?.fields?.map(field => <p key={field.field} className="field-error">{t(field.message)}</p>)}
    <FormGrid columns={3}>
      <FormField label={t("Full name")} required>{({ id }) => <Input id={id} icon="user" autoComplete="name" maxLength={150} required value={draft.full_name} onChange={e => setDraft({ ...draft, full_name: e.target.value })}/>}</FormField>
      <FormField label={t("Mobile number")}>{({ id }) => <Input id={id} icon="phone" type="tel" autoComplete="tel" maxLength={25} placeholder={t("Include country code, e.g. +94")} value={draft.phone_e164} onChange={e => setDraft({ ...draft, phone_e164: e.target.value })}/>}</FormField>
      <FormField label={t("Email address")}>{({ id }) => <Input id={id} icon="mail" readOnly value={user.email || t('Not provided')}/>}</FormField>
      <div className="ui-field"><span className="profile-static-label">{t("Email status")}</span><Chip tone={user.email_verified_at ? 'success' : 'muted'}>{user.email_verified_at ? t('Verified') : t('Unverified')}</Chip></div>
      <div className="ui-field"><span className="profile-static-label">{t("Phone status")}</span><Chip tone={user.phone_verified_at ? 'success' : 'muted'}>{user.phone_verified_at ? t('Verified') : t('Unverified')}</Chip></div>
      <div className="ui-field"><span className="profile-static-label">{t("Account role")}</span><span className="status-chips"><Chip tone="info">{t("Passenger")}</Chip>{roles.map(code => <Chip key={code} tone="info">{t(code === 'OWNER' ? 'Owner' : code === 'DRIVER' ? 'Driver' : 'Super Admin')}</Chip>)}</span></div>
    </FormGrid>
  </form>
}
