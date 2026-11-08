import { getLocale } from '../../i18n/language.js'
import { t } from '../../i18n/language.js'
import React, { useCallback, useEffect, useRef, useState } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'
import { api, hasSession, clearSession } from '../../services/api'
import { Header, Footer, ErrorNotice } from '../../components/components'
import PrivateDocumentPreview from '../../components/PrivateDocumentPreview'
import { actionLabel, roleActions, documentActions, needsReason, decisionPayload, mayReview } from './reviewRules'

const dateText = value => value ? new Date(value).toLocaleString(getLocale(), { timeZone: 'Asia/Colombo' }) + ' (Sri Lanka)' : '—'

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
  const [reviewNext, setReviewNext] = useState(null)
  const nextReviewHeading = useRef(null)
  const [reason, setReason] = useState('')
  const [confirm, setConfirm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const inflight = useRef(false)
  const confirmationHeading = useRef(null)

  useEffect(() => {
    if (action) confirmationHeading.current?.focus()
  }, [action])

  useEffect(() => {if(reviewNext)nextReviewHeading.current?.focus()},[reviewNext])

  const accessFailure = useCallback(err => {
    if ([401, 403].includes(err.status)) {
      generation.current += 1; setData(null); setPreview(null); setAction(null); setReviewNext(null); setAuthorized(false)
      if (err.status === 401) { clearSession(); navigate('/login', { replace: true }) }
      else setDenied(true)
    }
  }, [navigate])

  const load = useCallback(async ({ keepNotice = false } = {}) => {
    if (!keepNotice) setNotice('')
    const stamp = ++generation.current
    setLoading(true); setData(null); setPreview(null); setAction(null); setReviewNext(null); setConfirm(false); setError(null); setDenied(false)
    try {
      const user = await api('/users/me',{cache:'no-store'})
      if (stamp !== generation.current) return
      if (!mayReview(user)) { setAuthorized(false); setDenied(true); return }
      setAuthorized(true)
      const query = new URLSearchParams(Object.entries(filters).filter(([, v]) => v !== '')).toString()
      const result = await api(roleId ? `/admin/role-requests/${roleId}` : `/admin/role-requests?${query}`,{cache:'no-store'})
      if (stamp === generation.current) {setData(result); return result}
    } catch (err) { if (stamp === generation.current) { accessFailure(err); setError(err) } }
    finally { if (stamp === generation.current) setLoading(false) }
  }, [roleId, filters, accessFailure])

  useEffect(() => {
    document.title = 'Application review | Travelly'
    if (hasSession()) load()
    return () => { generation.current += 1 }
  }, [load])

  useEffect(() => {
    if (!roleId) return
    const refresh = () => {if(document.visibilityState==='visible'&&!loading&&!busy&&!action&&!preview)load()}
    window.addEventListener('focus',refresh)
    return () => window.removeEventListener('focus',refresh)
  },[roleId,load,loading,busy,action,preview])

  async function decide() {
    if (inflight.current) return
    inflight.current = true; setBusy(true); setError(null); setNotice('')
    const selected = action
    try {
      const body = decisionPayload(selected.decision, selected.version, reason)
      await api(`/admin/${selected.kind === 'role' ? 'role-requests' : 'documents'}/${selected.id}/review`, { method: 'PATCH', body: JSON.stringify(body) })
      setNotice(selected.kind==='role'?selected.decision==='APPROVED'?'Application approved. The applicant can now access the matching dashboard without reapplying.':selected.decision==='REJECTED'?'Application rejected. The applicant can see your reason in their application status.':'Role suspension saved.':'Document review saved. Continue reviewing this application.')
      const latest = await load({keepNotice:true})
      if(selected.kind==='document'&&selected.decision==='UNDER_REVIEW'){
        const doc=latest?.documents.find(item=>item.id===selected.id&&item.status==='UNDER_REVIEW')
        if(doc){setReviewNext(doc);setPreview(doc);setNotice('Review started. Inspect the document below, then choose Approve document, Reject document or Request correction.')}
      }
    } catch (err) {
      accessFailure(err)
      // Conflicts and uncertain outcomes always require an authoritative reload.
      if (err.status === 409 || err.status >= 500) await load()
      setError(err)
    } finally { inflight.current = false; setBusy(false) }
  }

  function choose(kind, record, decision) {
    setReviewNext(null)
    setAction({ kind, id: record.id, version: record.version, decision, label: kind === 'role' ? record.role_code : record.document_type })
    setReason(''); setConfirm(false)
  }
  if (!hasSession()) return <Navigate to="/login" replace/>
  return <div className="dashboard-page review-page">
    <Header dashboard><Link to="/">{t("booking home")}</Link>{authorized && <Link to="/admin/applications">{t("Application review")}</Link>}<Link to="/account">{t("Your profile")}</Link></Header>
    <main className="dashboard-main review-main" id="main">
      <div className="dashboard-section-heading"><div><span className="dashboard-kicker">{t("AUTHORIZED APPLICATION REVIEW")}</span><h1>{roleId ? t('Review application') : t('Owner & Driver applications')}</h1><p>{t("Independent role decisions. Passenger always stays available.")}</p></div>{roleId && <div className="review-actions"><Link className="button outline" to="/admin/applications">{t("Back to queue")}</Link><button type="button" className="button outline review-refresh" disabled={busy||loading} onClick={load}>{t("Refresh application")}</button></div>}</div>
      <ErrorNotice error={error}/>{notice && <p className="notice success" role="status">{t(notice)}</p>}
      {denied ? <section className="review-panel"><h2>{t("Review access denied")}</h2><p>{t("A current approved Admin membership is required. Self review is not permitted.")}</p><Link className="button" to="/">{t("Return to booking home")}</Link></section> : <>
        {!roleId && authorized && <form className="review-filters" aria-label={t("Application filters")} onSubmit={event => { event.preventDefault(); setFilters({ ...filters, q: search.trim(), page: 1 }) }}>
          <label>{t("Status")}<select aria-label={t("Status")} value={filters.status} disabled={busy} onChange={event => setFilters({ ...filters, status: event.target.value, page: 1 })}>{['PENDING', 'APPROVED', 'REJECTED', 'SUSPENDED', 'ALL'].map(s => <option value={s} key={s}>{t(s)}</option>)}</select></label>
          <label>{t("Application type")}<select aria-label={t("Application type")} value={filters.role_code} onChange={event => setFilters({ ...filters, role_code: event.target.value, page: 1 })}><option value="">{t("Owner and Driver")}</option><option value="OWNER">{t("Owner")}</option><option value="DRIVER">{t("Driver")}</option></select></label>
          <label>{t("Applicant name or reference")}<input maxLength={100} value={search} onChange={event => setSearch(event.target.value)}/></label><button className="button" disabled={busy}>{t("Search")}</button>
        </form>}
        {loading ? <p className="dashboard-loading" role="status">{t("Loading authorized review data…")}</p> : !data ? !error && <p>{t("Review data is unavailable.")}</p> : !roleId ? <section className="review-panel">
          {data.items.length ? <><p>{data.total}{t(" application")}{data.total === 1 ? '' : 's'}</p><div className="review-queue">{data.items.map(item => <article className="review-queue-row" key={item.id}><div><h2><Link to={`/admin/applications/${item.id}`}>{item.applicant.full_name}</Link></h2><p>{item.applicant.public_user_reference}</p></div><span>{t(item.role_code)}</span><span className={`dashboard-role-status status-${item.approval_status.toLowerCase()}`}>{item.approval_status==='PENDING'?t('Pending Review'):item.approval_status}</span><time>{dateText(item.requested_at)}</time><Link className="button outline" to={`/admin/applications/${item.id}`}>{t("Review application")}</Link></article>)}</div></> : <><h2>{filters.status === 'PENDING' && !filters.q && !filters.role_code ? t('No pending applications') : t('No applications match these filters')}</h2><p>{t("Only real Owner and Driver applications appear here.")}</p></>}
          <nav className="review-pagination" aria-label={t("Queue pages")}><button className="button outline" disabled={filters.page === 1} onClick={() => setFilters({ ...filters, page: filters.page - 1 })}>{t("Previous")}</button><span>{t("Page ")}{data.page}</span><button className="button outline" disabled={!data.has_next} onClick={() => setFilters({ ...filters, page: filters.page + 1 })}>{t("Next")}</button></nav>
        </section> : <>
          <section className="review-panel"><h2>{data.applicant.full_name} · {t(data.application.role_code)}</h2><span className={`dashboard-role-status status-${data.application.approval_status.toLowerCase()}`}>{data.application.approval_status==='PENDING'?t('Pending Review'):data.application.approval_status}</span>
            <dl className="review-identity">{[['Reference', data.applicant.public_user_reference], ['Email', data.applicant.email || 'Not supplied'], ['Mobile', data.applicant.phone_e164 || 'Not supplied'], ['Submitted', dateText(data.application.requested_at)], ['Contact verification', data.applicant.email_verified_at || data.applicant.phone_verified_at ? 'At least one contact verified' : 'Unverified · separate from role approval'], ['Current version', data.application.version]].map(([label, value]) => <div key={label}><dt>{t(label)}</dt><dd>{value}</dd></div>)}</dl>
            {(data.application.rejection_reason || data.application.suspension_reason) && <p className="review-reason">{data.application.rejection_reason || data.application.suspension_reason}</p>}
            <p>{data.application.role_code === 'OWNER' ? t('Required: verified NIC or Passport, plus applicant-owned vehicle registration or registered-owner/company authorization. Vehicle verification stays separate.') : t('Required: verified NIC or Passport, plus a Sri Lanka-issued driving licence with current expiry.')}</p>
            {data.application.approval_status==='PENDING'&&data.approval_readiness&&<section className="application-readiness" aria-label={t("Application review checklist")}><h3>{data.approval_readiness.ready?t('Ready for your decision'):t('Review the application documents')}</h3><ul>{data.approval_readiness.requirements.map(item=><li key={item.label}><strong>{t(item.label)}</strong><span>{t(item.message)}</span>{item.action&&<span>{t(item.action)}</span>}{!item.ready&&item.documents?.map(doc=><a className="evidence-review-link" key={doc.document_id} href={`#evidence-${doc.document_id}`}>{t("Go to ")}{data.documents.find(item=>item.id===doc.document_id)?.document_type.replaceAll('_', ' ') || t('document')}{t(" review")}</a>)}</li>)}</ul><p>{t("Review the submitted evidence below, then approve or reject this application. The applicant keeps the same application throughout review.")}</p></section>}
            <p id="approval-blocked" className="approval-blocked">{data.application.approval_status==='PENDING'&&data.approval_readiness?.ready===false?t('Approval blocked: complete the required document reviews above. Each document must be approved and current before Owner or Driver approval.'):null}</p>
            <div className="review-actions">{roleActions(data.application.approval_status).map(decision => <button className="button outline" key={decision} aria-describedby={decision==='APPROVED'&&data.approval_readiness?.ready===false?'approval-blocked':undefined} disabled={busy||(decision==='APPROVED'&&data.approval_readiness?.ready===false)} onClick={() => choose('role', data.application, decision)}>{t(actionLabel(decision))} {data.application.role_code === 'OWNER' ? t('Owner') : t('Driver')}</button>)}</div>
          </section>
          <section className="review-panel"><h2>{t("Private evidence")}</h2><p><strong>{t("Step 1:")}</strong>{t(" Start review and confirm. ")}<strong>{t("Step 2:")}</strong>{t(" Inspect the document, choose Approve document and confirm. Repeat for each required document before approving the role.")}</p><p>{t("Confirm the document matches this applicant and ownership case before verification. A correction request keeps the role PENDING.")}</p>
            {!data.documents.length && <p>{t("No current relevant evidence has been submitted. Approval requires the verified checklist.")}</p>}
            {data.documents.map(doc => <article className="review-document" id={`evidence-${doc.id}`} key={doc.id}><div><h3>{t(doc.document_type.replaceAll('_', ' '))}</h3><p>{t(doc.status)}{t(" · version ")}{doc.version}{doc.issuing_country && ` · ${doc.issuing_country}`}{doc.expiry_date && t(" · expires {value0}", {value0: doc.expiry_date})}</p>{doc.rejection_reason && <p className="review-reason">{doc.rejection_reason}</p>}</div><div className="review-actions"><button className="button outline" onClick={() => setPreview(doc)} disabled={busy}>{t("View private document")}</button>{documentActions(doc.status).map(decision => <button className="button outline" key={decision} disabled={busy} onClick={() => choose('document', doc, decision)}>{t(actionLabel(decision))}</button>)}</div></article>)}
          </section>
          {preview && <PrivateDocumentPreview key={preview.id} document={preview} onClose={() => setPreview(null)} onDenied={accessFailure}/>}
          {reviewNext && !action && <section className="review-panel document-verification-step" aria-label={t("Complete document verification")}><h2 ref={nextReviewHeading} tabIndex={-1}>{t("Step 2: Verify ")}{t(reviewNext.document_type.replaceAll('_',' '))}</h2><p>{t("Starting review has not approved this document. Inspect the private document above and check that it is current, readable and matches this applicant before recording your decision.")}</p><div className="review-actions">{documentActions(reviewNext.status).map(decision=><button type="button" className="button outline" key={decision} disabled={busy} onClick={()=>choose('document',reviewNext,decision)}>{decision==='APPROVED'?t('Approve document'):decision==='REJECTED'?t('Reject document'):actionLabel(decision)}</button>)}</div></section>}
          {action && <section className="review-panel review-confirmation" aria-label={t("Decision confirmation")}><h2 ref={confirmationHeading} tabIndex={-1}>{t(actionLabel(action.decision))} {t(action.label.replaceAll('_', ' '))}</h2><p>{data.applicant.full_name}{t(" · expected version ")}{action.version}{t(". This decision never removes Passenger membership.")}</p>{needsReason(action.decision) && <label>{t("Applicant-visible reason")}<textarea value={reason} maxLength={2000} rows={4} onChange={event => { setReason(event.target.value); setConfirm(false) }} disabled={busy}/><small>{reason.trim().length}{t("/2000 characters")}</small></label>}
            {!confirm ? <button className="button" disabled={busy || (needsReason(action.decision) && !reason.trim())} onClick={() => setConfirm(true)}>{t("Review confirmation")}</button> : <div role="alert"><p>{t("Confirm ")}{t(actionLabel(action.decision).toLowerCase())}{t(" for ")}{data.applicant.full_name}?{needsReason(action.decision) && t(' The applicant will see the complete reason below.')}</p>{needsReason(action.decision) && <blockquote className="review-reason">{reason.trim()}</blockquote>}<button className="button" disabled={busy} onClick={decide}>{busy ? t('Saving decision…') : t('Confirm decision')}</button></div>}<button className="button outline" disabled={busy} onClick={() => setAction(null)}>{t("Cancel")}</button>
          </section>}
        </>}
        {error && !denied && <button className="button outline" disabled={busy} onClick={load}>{t("Reload current data")}</button>}
      </>}
    </main><Footer/>
  </div>
}
