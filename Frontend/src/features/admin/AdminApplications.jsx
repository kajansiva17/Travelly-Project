import { getLocale } from '../../i18n/language.js'
import { t } from '../../i18n/language.js'
import React, { useCallback, useEffect, useRef, useState } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'
import { api, hasSession, clearSession } from '../../services/api'
import { Header, ErrorNotice } from '../../components/components'
import Chip from '../../components/ui/Chip'
import InfoTip from '../../components/ui/InfoTip'
import { Field, Compact } from '../owner/OwnerRates'
import { FlowShell, usePaged, useRowCount } from '../booking/flow/FlowParts'
import { Notice, Empty } from '../ticketing/TicketParts'
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
  const [view, setView] = useState(0)
  const docs = usePaged(data?.documents || [], Math.max(1, useRowCount(92)))
  const queue = usePaged(data?.items || [], Math.max(2, useRowCount(92)))

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
  const app = data?.application, person = data?.applicant
  const statusTone = value => value === 'APPROVED' ? 'success' : ['REJECTED', 'SUSPENDED'].includes(value) ? 'danger' : 'muted'
  const statusText = value => value === 'PENDING' ? t('Pending Review') : value
  const detail = Boolean(roleId && app && person)
  const tabs = detail && !action ? [{ label: t('Application'), icon: 'users', active: view === 0, onClick: () => setView(0) }, { label: t('Evidence'), icon: 'document', active: view === 1, onClick: () => setView(1) }] : undefined
  const title = action ? `${t(actionLabel(action.decision))} ${t(action.label.replaceAll('_', ' '))}` : detail ? `${person.full_name} · ${t(app.role_code)}` : roleId ? t('Review application') : t('Owner & Driver applications')
  const decisionBar = detail && !action && <>{roleActions(app.approval_status).map(decision => <button type="button" className="ui-button ui-button-secondary" key={decision} aria-describedby={decision === 'APPROVED' && data.approval_readiness?.ready === false ? 'approval-blocked' : undefined} disabled={busy || (decision === 'APPROVED' && data.approval_readiness?.ready === false)} onClick={() => choose('role', app, decision)}>{t(actionLabel(decision))} {app.role_code === 'OWNER' ? t('Owner') : t('Driver')}</button>)}</>
  return <><Header/><FlowShell heading={t('Application review')} icon="users" title={title} tabs={tabs} info={t("Independent role decisions. Passenger always stays available.")}>
    <Compact.Provider value={true}>
    <ErrorNotice error={error}/><Notice>{notice ? t(notice) : ''}</Notice>
    {denied ? <><Empty>{t("A current approved Admin membership is required. Self review is not permitted.")}</Empty><div className="flow-actions"><span/><Link className="ui-button ui-button-primary" to="/">{t("Return to booking home")}</Link></div></>
    : loading ? <p role="status">{t("Loading authorized review data…")}</p>
    : !data ? (!error && <Empty>{t("Review data is unavailable.")}</Empty>)
    : !roleId ? <>
      {authorized && <div><form className="tk-grid" style={{ '--cols': 4, gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1.3fr) auto' }} aria-label={t("Application filters")} onSubmit={event => { event.preventDefault(); setFilters({ ...filters, q: search.trim(), page: 1 }) }}>
        <Field label="Status"><select aria-label={t("Status")} value={filters.status} disabled={busy} onChange={event => setFilters({ ...filters, status: event.target.value, page: 1 })}>{['PENDING', 'APPROVED', 'REJECTED', 'SUSPENDED', 'ALL'].map(s => <option value={s} key={s}>{t(s)}</option>)}</select></Field>
        <Field label="Application type"><select aria-label={t("Application type")} value={filters.role_code} onChange={event => setFilters({ ...filters, role_code: event.target.value, page: 1 })}><option value="">{t("Owner and Driver")}</option><option value="OWNER">{t("Owner")}</option><option value="DRIVER">{t("Driver")}</option></select></Field>
        <Field label="Applicant name or reference" optional><input maxLength={100} value={search} onChange={event => setSearch(event.target.value)}/></Field>
        <div style={{ alignSelf: 'end' }}><button className="ui-button ui-button-primary" disabled={busy}>{t("Search")}</button></div>
      </form></div>}
      <div className="tk-pane">{(data.items || []).length
        ? <div className="tk-rows">{queue.slice.map(item => <article className="tk-row" key={item.id}><div className="tk-row-main"><strong><Link to={`/admin/applications/${item.id}`}>{item.applicant?.full_name}</Link></strong><span>{item.applicant?.public_user_reference} · {t(item.role_code)} · {dateText(item.requested_at)}</span></div>
          <div className="tk-row-actions"><Chip tone={statusTone(item.approval_status)}>{statusText(item.approval_status)}</Chip><Link className="ui-button ui-button-secondary" to={`/admin/applications/${item.id}`}>{t("Review application")}</Link></div></article>)}</div>
        : <Empty>{filters.status === 'PENDING' && !filters.q && !filters.role_code ? t('No pending applications') : t('No applications match these filters')}</Empty>}</div>
      <div className="flow-actions"><span className="tk-line">{data.total}{t(" application")}{data.total === 1 ? '' : 's'}</span>{queue.pages > 1 && queue.pager}
        <nav className="flow-pager" aria-label={t("Queue pages")}><button type="button" className="ui-button ui-button-secondary" disabled={filters.page === 1} onClick={() => setFilters({ ...filters, page: filters.page - 1 })}>{t("Previous")}</button><span>{t("Page ")}{data.page}</span><button type="button" className="ui-button ui-button-secondary" disabled={!data.has_next} onClick={() => setFilters({ ...filters, page: filters.page + 1 })}>{t("Next")}</button></nav></div>
    </>
    : !detail ? <><Empty>{t("Review data is unavailable.")}</Empty><div className="flow-actions"><Link className="ui-button ui-button-secondary" to="/admin/applications">{t("Back to queue")}</Link></div></>
    : action ? <>
      <div className="tk-pane"><p className="tk-line" ref={confirmationHeading} tabIndex={-1}>{person.full_name}{t(" · expected version ")}{action.version}{t(". This decision never removes Passenger membership.")}</p>
        {needsReason(action.decision) && <Field label="Applicant-visible reason"><textarea value={reason} maxLength={2000} rows={3} onChange={event => { setReason(event.target.value); setConfirm(false) }} disabled={busy}/></Field>}
        {needsReason(action.decision) && <small className="tk-line">{reason.trim().length}{t("/2000 characters")}</small>}
        {confirm && <div role="alert"><p className="tk-line">{t("Confirm ")}{t(actionLabel(action.decision).toLowerCase())}{t(" for ")}{person.full_name}?{needsReason(action.decision) && t(' The applicant will see the complete reason below.')}</p>{needsReason(action.decision) && <blockquote className="review-reason">{reason.trim()}</blockquote>}</div>}</div>
      <div className="flow-actions"><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={() => setAction(null)}>{t("Cancel")}</button>
        {!confirm ? <button key="review" type="button" className="ui-button ui-button-primary" disabled={busy || (needsReason(action.decision) && !reason.trim())} onClick={() => setConfirm(true)}>{t("Review confirmation")}</button> : <button key="confirm" type="button" className="ui-button ui-button-primary" disabled={busy} onClick={decide}>{busy ? t('Saving decision…') : t('Confirm decision')}</button>}</div>
    </>
    : view === 0 ? <>
      <div className="tk-bar"><Chip tone={statusTone(app.approval_status)}>{statusText(app.approval_status)}</Chip><InfoTip>{app.role_code === 'OWNER' ? t('Required: verified NIC or Passport, plus applicant-owned vehicle registration or registered-owner/company authorization. Vehicle verification stays separate.') : t('Required: verified NIC or Passport, plus a Sri Lanka-issued driving licence with current expiry.')}</InfoTip></div>
      <dl className="tk-facts">{[['Reference', person.public_user_reference], ['Email', person.email || 'Not supplied'], ['Mobile', person.phone_e164 || 'Not supplied'], ['Submitted', dateText(app.requested_at)], ['Contact verification', person.email_verified_at || person.phone_verified_at ? 'At least one contact verified' : 'Unverified · separate from role approval'], ['Current version', app.version]].map(([label, value]) => <div key={label}><dt>{t(label)}</dt><dd title={String(value ?? '')}>{value}</dd></div>)}</dl>
      {(app.rejection_reason || app.suspension_reason) && <p className="tk-line is-warn">{app.rejection_reason || app.suspension_reason}</p>}
      {app.approval_status === 'PENDING' && data.approval_readiness && <div className="tk-bar" aria-label={t("Application review checklist")}><strong className="tk-line">{data.approval_readiness.ready ? t('Ready for your decision') : t('Review the application documents')}</strong>
        {(data.approval_readiness.requirements || []).map(item => <span key={item.label} className="tk-chips"><Chip tone={item.ready ? 'success' : 'danger'} icon={item.ready ? undefined : 'alert'}>{t(item.label)}</Chip><InfoTip>{t(item.message)}{item.action ? ' ' + t(item.action) : ''}</InfoTip></span>)}</div>}
      <p id="approval-blocked" className="tk-line is-warn">{app.approval_status === 'PENDING' && data.approval_readiness?.ready === false ? t('Approval blocked: complete the required document reviews above. Each document must be approved and current before Owner or Driver approval.') : null}</p>
      <div className="flow-actions"><Link className="ui-button ui-button-secondary" to="/admin/applications">{t("Back to queue")}</Link><button type="button" className="ui-button ui-button-secondary review-refresh" disabled={busy || loading} onClick={load}>{t("Refresh application")}</button>{decisionBar}</div>
    </>
    : <>
      <div className="tk-bar"><strong className="tk-line">{t("Private evidence")}</strong><InfoTip>{t("Step 1:")}{t(" Start review and confirm. ")}{t("Step 2:")}{t(" Inspect the document, choose Approve document and confirm. Repeat for each required document before approving the role.")} {t("Confirm the document matches this applicant and ownership case before verification. A correction request keeps the role PENDING.")}</InfoTip></div>
      {reviewNext && <div className="tk-bar" aria-label={t("Complete document verification")}><strong className="tk-line" ref={nextReviewHeading} tabIndex={-1}>{t("Step 2: Verify ")}{t(reviewNext.document_type.replaceAll('_', ' '))}</strong><InfoTip>{t("Starting review has not approved this document. Inspect the private document above and check that it is current, readable and matches this applicant before recording your decision.")}</InfoTip>
        {documentActions(reviewNext.status).map(decision => <button type="button" className="ui-button ui-button-secondary" key={decision} disabled={busy} onClick={() => choose('document', reviewNext, decision)}>{decision === 'APPROVED' ? t('Approve document') : decision === 'REJECTED' ? t('Reject document') : t(actionLabel(decision))}</button>)}</div>}
      <div className="tk-pane">{!(data.documents || []).length && <Empty>{t("No current relevant evidence has been submitted. Approval requires the verified checklist.")}</Empty>}
        <div className="tk-rows">{docs.slice.map(doc => <article className="tk-row" id={`evidence-${doc.id}`} key={doc.id}><div className="tk-row-main"><strong>{t((doc.document_type || '').replaceAll('_', ' '))}</strong><span>{t(doc.status)}{t(" · version ")}{doc.version}{doc.issuing_country && ` · ${doc.issuing_country}`}{doc.expiry_date && t(" · expires {value0}", { value0: doc.expiry_date })}{doc.rejection_reason && ` · ${doc.rejection_reason}`}</span></div>
          <div className="tk-row-actions"><button type="button" className="ui-button ui-button-secondary" onClick={() => setPreview(doc)} disabled={busy}>{t("View private document")}</button>{documentActions(doc.status).map(decision => <button type="button" className="ui-button ui-button-secondary" key={decision} disabled={busy} onClick={() => choose('document', doc, decision)}>{t(actionLabel(decision))}</button>)}</div></article>)}</div></div>
      <div className="flow-actions"><Link className="ui-button ui-button-secondary" to="/admin/applications">{t("Back to queue")}</Link>{docs.pages > 1 && docs.pager}</div>
    </>}
    {preview && <PrivateDocumentPreview key={preview.id} document={preview} onClose={() => setPreview(null)} onDenied={accessFailure}/>}
    {error && !denied && <div className="tk-bar"><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={load}>{t("Reload current data")}</button></div>}
    </Compact.Provider>
  </FlowShell></>
}
