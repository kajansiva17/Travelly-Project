import React, { useCallback, useEffect, useRef, useState } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'
import { api, hasSession, clearSession } from './api'
import { Header, Footer, ErrorNotice } from './components'
import PrivateDocumentPreview from './PrivateDocumentPreview'
import { actionLabel, roleActions, documentActions, needsReason, decisionPayload, mayReview } from './reviewRules'

const dateText = value => value ? new Date(value).toLocaleString('en-GB', { timeZone: 'Asia/Colombo' }) + ' (Sri Lanka)' : '—'

export default function AdminApplications() {
  const { roleId } = useParams()
  const navigate = useNavigate()
  const generation = useRef(0)
  const [authorized, setAuthorized] = useState(false)
  const [denied, setDenied] = useState(false)
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState({ status: 'PENDING', role_code: '', q: '', page: 1 })
  const [search, setSearch] = useState('')
  const [preview, setPreview] = useState(null)
  const [action, setAction] = useState(null)
  const [reason, setReason] = useState('')
  const [confirm, setConfirm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const inflight = useRef(false)

  const accessFailure = useCallback(err => {
    if ([401, 403].includes(err.status)) {
      generation.current += 1; setData(null); setPreview(null); setAction(null); setAuthorized(false)
      if (err.status === 401) { clearSession(); navigate('/login', { replace: true }) }
      else setDenied(true)
    }
  }, [navigate])

  const load = useCallback(async () => {
    const stamp = ++generation.current
    setLoading(true); setData(null); setPreview(null); setAction(null); setConfirm(false); setError(null); setDenied(false)
    try {
      const user = await api('/users/me')
      if (stamp !== generation.current) return
      if (!mayReview(user)) { setAuthorized(false); setDenied(true); return }
      setAuthorized(true)
      const query = new URLSearchParams(Object.entries(filters).filter(([, v]) => v !== '')).toString()
      const result = await api(roleId ? `/admin/role-requests/${roleId}` : `/admin/role-requests?${query}`)
      if (stamp === generation.current) setData(result)
    } catch (err) { if (stamp === generation.current) { accessFailure(err); setError(err) } }
    finally { if (stamp === generation.current) setLoading(false) }
  }, [roleId, filters, accessFailure])

  useEffect(() => {
    document.title = 'Application review | Travelly'
    if (hasSession()) load()
    return () => { generation.current += 1 }
  }, [load])

  async function decide() {
    if (inflight.current) return
    inflight.current = true; setBusy(true); setError(null); setNotice('')
    const selected = action
    try {
      const body = decisionPayload(selected.decision, selected.version, reason)
      await api(`/admin/${selected.kind === 'role' ? 'role-requests' : 'documents'}/${selected.id}/review`, { method: 'PATCH', body: JSON.stringify(body) })
      setNotice('Decision saved. Passenger membership and contact verification are unchanged.')
      await load()
    } catch (err) {
      accessFailure(err)
      // Conflicts and uncertain outcomes always require an authoritative reload.
      if (err.status === 409 || err.status >= 500) await load()
      setError(err)
    } finally { inflight.current = false; setBusy(false) }
  }

  function choose(kind, record, decision) {
    setAction({ kind, id: record.id, version: record.version, decision, label: kind === 'role' ? record.role_code : record.document_type })
    setReason(''); setConfirm(false)
  }
  if (!hasSession()) return <Navigate to="/login" replace/>
  return <div className="dashboard-page review-page">
    <Header dashboard><Link to="/dashboard">Passenger dashboard</Link>{authorized && <Link to="/admin/applications">Application review</Link>}<Link to="/account">Your profile</Link></Header>
    <main className="dashboard-main review-main" id="main">
      <div className="dashboard-section-heading"><div><span className="dashboard-kicker">AUTHORIZED APPLICATION REVIEW</span><h1>{roleId ? 'Review application' : 'Owner & Driver applications'}</h1><p>Independent role decisions. Passenger always stays available.</p></div>{roleId && <Link className="button outline" to="/admin/applications">Back to queue</Link>}</div>
      <ErrorNotice error={error}/>{notice && <p className="notice success" role="status">{notice}</p>}
      {denied ? <section className="review-panel"><h2>Review access denied</h2><p>A current approved Admin membership is required. Self review is not permitted.</p><Link className="button" to="/dashboard">Return to Passenger dashboard</Link></section> : <>
        {!roleId && authorized && <form className="review-filters" aria-label="Application filters" onSubmit={event => { event.preventDefault(); setFilters({ ...filters, q: search.trim(), page: 1 }) }}>
          <label>Status<select aria-label="Status" value={filters.status} disabled={busy} onChange={event => setFilters({ ...filters, status: event.target.value, page: 1 })}>{['PENDING', 'APPROVED', 'REJECTED', 'SUSPENDED', 'ALL'].map(s => <option key={s}>{s}</option>)}</select></label>
          <label>Application type<select aria-label="Application type" value={filters.role_code} onChange={event => setFilters({ ...filters, role_code: event.target.value, page: 1 })}><option value="">Owner and Driver</option><option value="OWNER">Owner</option><option value="DRIVER">Driver</option></select></label>
          <label>Applicant name or reference<input maxLength={100} value={search} onChange={event => setSearch(event.target.value)}/></label><button className="button" disabled={busy}>Search</button>
        </form>}
        {loading ? <p className="dashboard-loading" role="status">Loading authorized review data…</p> : !data ? !error && <p>Review data is unavailable.</p> : !roleId ? <section className="review-panel">
          {data.items.length ? <><p>{data.total} application{data.total === 1 ? '' : 's'}</p><div className="review-queue">{data.items.map(item => <article className="review-queue-row" key={item.id}><div><h2><Link to={`/admin/applications/${item.id}`}>{item.applicant.full_name}</Link></h2><p>{item.applicant.public_user_reference}</p></div><span>{item.role_code}</span><span className={`dashboard-role-status status-${item.approval_status.toLowerCase()}`}>{item.approval_status}</span><time>{dateText(item.requested_at)}</time><Link className="button outline" to={`/admin/applications/${item.id}`}>Review application</Link></article>)}</div></> : <><h2>{filters.status === 'PENDING' && !filters.q && !filters.role_code ? 'No pending applications' : 'No applications match these filters'}</h2><p>Only real Owner and Driver applications appear here.</p></>}
          <nav className="review-pagination" aria-label="Queue pages"><button className="button outline" disabled={filters.page === 1} onClick={() => setFilters({ ...filters, page: filters.page - 1 })}>Previous</button><span>Page {data.page}</span><button className="button outline" disabled={!data.has_next} onClick={() => setFilters({ ...filters, page: filters.page + 1 })}>Next</button></nav>
        </section> : <>
          <section className="review-panel"><h2>{data.applicant.full_name} · {data.application.role_code}</h2><span className={`dashboard-role-status status-${data.application.approval_status.toLowerCase()}`}>{data.application.approval_status}</span>
            <dl className="review-identity">{[['Reference', data.applicant.public_user_reference], ['Email', data.applicant.email || 'Not supplied'], ['Mobile', data.applicant.phone_e164 || 'Not supplied'], ['Submitted', dateText(data.application.requested_at)], ['Contact verification', data.applicant.email_verified_at || data.applicant.phone_verified_at ? 'At least one contact verified' : 'Unverified · separate from role approval'], ['Current version', data.application.version]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
            {(data.application.rejection_reason || data.application.suspension_reason) && <p className="review-reason">{data.application.rejection_reason || data.application.suspension_reason}</p>}
            <p>{data.application.role_code === 'OWNER' ? 'Required: verified NIC or Passport, plus applicant-owned vehicle registration or registered-owner/company authorization. Vehicle verification stays separate.' : 'Required: verified NIC or Passport, plus a Sri Lanka-issued driving licence with current expiry.'}</p>
            <div className="review-actions">{roleActions(data.application.approval_status).map(decision => <button className="button outline" key={decision} disabled={busy} onClick={() => choose('role', data.application, decision)}>{actionLabel(decision)} {data.application.role_code === 'OWNER' ? 'Owner' : 'Driver'}</button>)}</div>
          </section>
          <section className="review-panel"><h2>Private evidence</h2><p>Confirm the document matches this applicant and ownership case before verification. A correction request keeps the role PENDING.</p>
            {!data.documents.length && <p>No current relevant evidence has been submitted. Approval requires the verified checklist.</p>}
            {data.documents.map(doc => <article className="review-document" key={doc.id}><div><h3>{doc.document_type.replaceAll('_', ' ')}</h3><p>{doc.status} · version {doc.version}{doc.issuing_country && ` · ${doc.issuing_country}`}{doc.expiry_date && ` · expires ${doc.expiry_date}`}</p>{doc.rejection_reason && <p className="review-reason">{doc.rejection_reason}</p>}</div><div className="review-actions"><button className="button outline" onClick={() => setPreview(doc)} disabled={busy}>View private document</button>{documentActions(doc.status).map(decision => <button className="button outline" key={decision} disabled={busy} onClick={() => choose('document', doc, decision)}>{actionLabel(decision)}</button>)}</div></article>)}
          </section>
          {preview && <PrivateDocumentPreview key={preview.id} document={preview} onClose={() => setPreview(null)} onDenied={accessFailure}/>}
          {action && <section className="review-panel review-confirmation" aria-label="Decision confirmation"><h2>{actionLabel(action.decision)} {action.label.replaceAll('_', ' ')}</h2><p>{data.applicant.full_name} · expected version {action.version}. This decision never removes Passenger membership.</p>{needsReason(action.decision) && <label>Applicant-visible reason<textarea value={reason} maxLength={2000} rows={4} onChange={event => { setReason(event.target.value); setConfirm(false) }} disabled={busy}/><small>{reason.trim().length}/2000 characters</small></label>}
            {!confirm ? <button className="button" disabled={busy || (needsReason(action.decision) && !reason.trim())} onClick={() => setConfirm(true)}>Review confirmation</button> : <div role="alert"><p>Confirm {actionLabel(action.decision).toLowerCase()} for {data.applicant.full_name}?{needsReason(action.decision) && ' The applicant will see the complete reason below.'}</p>{needsReason(action.decision) && <blockquote className="review-reason">{reason.trim()}</blockquote>}<button className="button" disabled={busy} onClick={decide}>{busy ? 'Saving decision…' : 'Confirm decision'}</button></div>}<button className="button outline" disabled={busy} onClick={() => setAction(null)}>Cancel</button>
          </section>}
        </>}
        {error && !denied && <button className="button outline" disabled={busy} onClick={load}>Reload current data</button>}
      </>}
    </main><Footer/>
  </div>
}
