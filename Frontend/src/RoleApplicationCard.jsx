import React from 'react'
import { Link } from 'react-router-dom'
import { ErrorNotice, Icon } from './components'

const labels = { PENDING: 'Application pending', APPROVED: 'Approved', REJECTED: 'Application rejected', SUSPENDED: 'Role suspended' }

// Application details live within the contract's /dashboard route. Hashes are
// section anchors, not additional application/workspace routes.
export default function RoleApplicationCard({ code, role, user, busy, apply, expanded, error, workspace }) {
  const owner = code === 'OWNER'
  const name = owner ? 'Owner' : 'Driver'
  const anchor = `${code.toLowerCase()}-application`
  const approved = role?.approval_status === 'APPROVED'
  const mayApply = !role || role.approval_status === 'REJECTED'
  const verified = Boolean(user.email_verified_at || user.phone_verified_at)
  return <article className="dashboard-application" id={anchor} aria-label={`${name} application`}>
    <span className="dashboard-app-icon"><Icon name={owner ? 'car' : 'user'} size={27}/></span>
    <div className="dashboard-application-copy">
      <h3>{approved ? `${name}-ready` : owner ? 'Become an Owner' : 'Drive with Travelly'}</h3>
      <p>{approved ? 'Your role is approved. Operational eligibility is checked separately.' : owner ? 'Have a vehicle? Start your Owner application with this account.' : 'Take the next step. Apply for Driver membership with this account.'}</p>
      {role && <span className={`dashboard-role-status status-${role.approval_status.toLowerCase()}`}>{labels[role.approval_status]}</span>}
      {role?.approval_status === 'REJECTED' && role.rejection_reason && <p className="dashboard-role-reason">{role.rejection_reason}</p>}
      {role?.approval_status === 'SUSPENDED' && role.suspension_reason && <p className="dashboard-role-reason">{role.suspension_reason}</p>}
      {role?.approval_status === 'PENDING' && <small>Your application has been received. You can continue as a Passenger while approval is pending.</small>}
      {role?.approval_status === 'SUSPENDED' && <small>This role needs an authorized review. It cannot be reinstated from your Passenger dashboard.</small>}
      {!expanded && <Link className="button outline" to={`/dashboard#${anchor}`} aria-expanded="false" aria-controls={`${anchor}-details`}>{mayApply ? role ? 'Apply again' : 'Start application' : 'View application'}<Icon name="arrow" size={18}/></Link>}
      {approved && <button type="button" className="inline-link" onClick={workspace}>{name} workspace · coming soon</button>}

      {expanded && <section className="application-details" id={`${anchor}-details`} aria-labelledby={`${anchor}-title`}>
        <h4 id={`${anchor}-title`}>{role ? `${name} application details` : `Review your ${name} application`}</h4>
        <dl className="application-profile">
          <div><dt>Full name</dt><dd>{user.full_name}</dd></div>
          {user.email && <div><dt>Email address</dt><dd>{user.email}</dd></div>}
          {user.phone_e164 && <div><dt>Mobile number</dt><dd>{user.phone_e164}</dd></div>}
          <div><dt>Requested role</dt><dd>{name}</dd></div>
          <div><dt>Contact verification</dt><dd>{verified ? 'At least one contact verified' : 'Awaiting contact verification'}</dd></div>
          {role && <div><dt>Application status</dt><dd>{labels[role.approval_status]}</dd></div>}
        </dl>
        <p className="application-membership-note"><Icon name="shield" size={19}/> Your Passenger membership and default workspace stay unchanged. Owner and Driver are reviewed independently.</p>
        <p className="application-document-note">Submit your private evidence from your profile. Admin reviews evidence and your role separately. Submitting this request does not verify your contact or approve this role.</p>
        <Link className="inline-link" to="/account">Manage your private documents</Link>
        {error && <ErrorNotice error={error}/>}
        {mayApply ? <form aria-label={`${name} application form`} onSubmit={event => { event.preventDefault(); apply(code) }}>
          <p>{role ? 'Resubmitting sends this same application back to PENDING for review.' : 'Submit a membership request using your existing Travelly profile. Your application will start as PENDING.'}</p>
          <button type="submit" className="button" disabled={busy}>{busy ? 'Submitting…' : role ? `Resubmit ${name} application` : `Submit ${name} application`}<Icon name="arrow" size={18}/></button>
        </form> : role?.approval_status === 'PENDING' ? <p className="application-next-step">Approval is pending. You can continue using Passenger features and apply for the other role independently.</p> : role?.approval_status === 'SUSPENDED' ? <p className="application-next-step">An authorized review is required. A new request or replacement document cannot reinstate this role. You can still use your Passenger workspace.</p> : <p className="application-next-step">Your role is approved. This does not guarantee document or operational eligibility; the operational workspace is not available yet.</p>}
        <Link className="inline-link application-back" to="/dashboard#applications-heading">Back to Passenger overview</Link>
      </section>}
    </div>
  </article>
}
