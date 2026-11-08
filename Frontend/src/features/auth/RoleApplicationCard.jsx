import { t } from '../../i18n/language.js'
import React from 'react'
import { Link } from 'react-router-dom'
import { Icon } from '../../components/components'

const labels = { PENDING: 'Application pending', APPROVED: 'Approved', REJECTED: 'Application rejected', SUSPENDED: 'Role suspended' }

// Role applications belong to the shared account, separate from operational workspaces.
export default function RoleApplicationCard({ code, role, user, busy, apply }) {
  const owner = code === 'OWNER'
  const name = owner ? 'Owner' : 'Driver'
  const anchor = `${code.toLowerCase()}-application`
  const approved = role?.approval_status === 'APPROVED'
  const mayApply = !role || role.approval_status === 'REJECTED'
  const verified = Boolean(user.email_verified_at || user.phone_verified_at)
  return <article className="dashboard-application" id={anchor} aria-label={t("{value0} application", {value0: name})}>
    <span className="dashboard-app-icon"><Icon name={owner ? 'car' : 'user'} size={27}/></span>
    <div className="dashboard-application-copy">
      <h3>{approved ? t("{value0}-ready", {value0: name}) : owner ? t('Become an Owner') : t('Drive with Travelly')}</h3>
      <p>{approved ? t('Your role is approved. Operational eligibility is checked separately.') : owner ? t('Have a vehicle? Start your Owner application with this account.') : t('Take the next step. Apply for Driver membership with this account.')}</p>
      {role && <span className={`dashboard-role-status status-${role.approval_status.toLowerCase()}`}>{t(labels[role.approval_status])}</span>}
      {role?.approval_status === 'REJECTED' && role.rejection_reason && <p className="dashboard-role-reason">{role.rejection_reason}</p>}
      {role?.approval_status === 'SUSPENDED' && role.suspension_reason && <p className="dashboard-role-reason">{role.suspension_reason}</p>}
      {role?.approval_status === 'PENDING' && <small>{t("Your application has been received. You can continue as a Passenger while approval is pending.")}</small>}
      {role?.approval_status === 'SUSPENDED' && <small>{t("This role needs an authorized review. It cannot be reinstated from your account.")}</small>}
      <section className="application-details" id={`${anchor}-details`} aria-labelledby={`${anchor}-title`}>
        <h4 id={`${anchor}-title`}>{role ? t("{value0} application details", {value0: name}) : t("Review your {value0} application", {value0: name})}</h4>
        <dl className="application-profile">
          <div><dt>{t("Full name")}</dt><dd>{user.full_name}</dd></div>
          {user.email && <div><dt>{t("Email address")}</dt><dd>{user.email}</dd></div>}
          {user.phone_e164 && <div><dt>{t("Mobile number")}</dt><dd>{user.phone_e164}</dd></div>}
          <div><dt>{t("Requested role")}</dt><dd>{t(name)}</dd></div>
          <div><dt>{t("Contact verification")}</dt><dd>{verified ? t('At least one contact verified') : t('Awaiting contact verification')}</dd></div>
          {role && <div><dt>{t("Application status")}</dt><dd>{t(labels[role.approval_status])}</dd></div>}
        </dl>
        <p className="application-membership-note"><Icon name="shield" size={19}/>{t(" Your Passenger membership stays unchanged. Owner and Driver are reviewed independently.")}</p>
        <p className="application-document-note">{t("Submit private evidence in the document flow for this application. Admin reviews evidence and your role separately. Submitting this request does not verify your contact or approve this role.")}</p>
        <Link className="inline-link" to={`/${code.toLowerCase()}/onboarding#own-documents-heading`}>{t("Manage your ")}{t(name)}{t(" application documents")}</Link>
        {mayApply ? <form aria-label={t("{value0} application form", {value0: name})} onSubmit={event => { event.preventDefault(); apply(code) }}>
          <p>{role ? t('Resubmitting sends this same application back to PENDING for review.') : t('Submit a membership request using your existing Travelly profile. Your application will start as PENDING.')}</p>
          <button type="submit" className="button" disabled={busy}>{busy ? t('Submitting…') : role ? t("Resubmit {value0} application", {value0: name}) : t("Submit {value0} application", {value0: name})}<Icon name="arrow" size={18}/></button>
        </form> : role?.approval_status === 'PENDING' ? <p className="application-next-step">{t("Approval is pending. You can continue using Passenger features and apply for the other role independently.")}</p> : role?.approval_status === 'SUSPENDED' ? <p className="application-next-step">{t("An authorized review is required. A new request or replacement document cannot reinstate this role. You can still use your booking experience.")}</p> : <p className="application-next-step">{t("Your role is approved. This does not guarantee document or operational eligibility; open your workspace to review the actions currently available.")}</p>}
      </section>
    </div>
  </article>
}
