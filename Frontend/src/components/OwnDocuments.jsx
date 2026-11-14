import { t } from '../i18n/language.js'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import { ErrorNotice } from './components'
import PrivateDocumentPreview from './PrivateDocumentPreview'
import DocumentUploadForm from './DocumentUploadForm'
import Chip from './ui/Chip'
import InfoTip from './ui/InfoTip'
import {usePaged,useRowCount} from '../features/booking/flow/FlowParts'
import {codeLabel} from '../i18n/codeLabels.js'

export default function OwnDocuments({ user, flow = 'SHARED', evidencePath }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [preview, setPreview] = useState(null)
  const [page, setPage] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const [loading, setLoading] = useState(false)
  const [library,setLibrary]=useState(false)
  const sequence = useRef(0), pending = useRef(false)
  const load = useCallback(async (targetPage = 1) => {
    if (pending.current) return
    pending.current = true
    const current = ++sequence.current
    setError(null); setLoading(true)
    try {
      const result = await api(`/documents?user_id=${user.id}&page=${targetPage}&page_size=20`)
      if (current !== sequence.current) return
      setItems(result.items); setHasNext(result.has_next); setPage(targetPage)
    } catch (err) { if (current === sequence.current) setError(err) }
    finally { if (current === sequence.current) { pending.current = false; setLoading(false) } }
  }, [user.id])
  useEffect(() => { load(1); return () => { sequence.current += 1; pending.current = false } }, [load])
  const title = flow === 'OWNER' ? 'Owner application documents' : flow === 'DRIVER' ? 'Driver application documents' : 'Your private documents'
  const types=flow==='OWNER'?['NIC','PASSPORT','VEHICLE_REGISTRATION','OWNER_AUTHORISATION']:flow==='DRIVER'?['NIC','PASSPORT','DRIVING_LICENCE']:['NIC','PASSPORT']
  const visible=library?items:items?.filter(doc=>types.includes(doc.document_type))
  const rows=usePaged(visible,useRowCount(56)),[uploading,setUploading]=useState(false)
  return <section className="own-documents" aria-labelledby="own-documents-heading">
    <div className="own-documents-head"><h2 id="own-documents-heading">{uploading?t('Upload one document'):library?t('Retained private documents'):t(title)}<InfoTip>{t("Correct a reviewed file by submitting a new document of the same type in its matching evidence flow. Earlier files and reasons are retained; replacing a file does not reinstate a suspended role.")}</InfoTip></h2>
      <span className="status-chips">{!uploading&&<button type="button" className="ui-button ui-button-secondary" onClick={()=>{setPreview(null);setLibrary(!library)}}>{library?t("Back to {value0} documents", {value0: flow==='SHARED'?'shared identity':flow==='OWNER'?'Owner':'Driver'}):t('View all retained documents')}</button>}
        {!library&&<button type="button" className="ui-button ui-button-primary" onClick={()=>setUploading(!uploading)}>{uploading?t('Back to documents'):t('Upload one document')}</button>}</span></div>
    {uploading&&!library&&<DocumentUploadForm user={user} flow={flow} onUploaded={async()=>{await load(page);setUploading(false)}}/>}
    <ErrorNotice error={error}/>
    {!uploading&&<div className="own-documents-list" aria-busy={loading}>
      {loading && <p role="status">{t("Loading your documents…")}</p>}
      {items?.length === 0 && <p className="flow-note">{t("No private documents submitted yet.")}</p>}
      {items?.length>0&&visible.length===0&&<p className="flow-note">{t("No matching evidence on this page. Browse the other pages or view all retained documents.")}</p>}
      {rows.slice.map(doc => {const code=['VEHICLE_REGISTRATION','OWNER_AUTHORISATION'].includes(doc.document_type)?'OWNER':doc.document_type==='DRIVING_LICENCE'?'DRIVER':null;return <article className="review-document own-document-row" key={doc.id}><strong>{codeLabel(doc.document_type)}</strong><Chip tone={doc.status==='APPROVED'?'success':/REJECT|CORRECTION|SUSPEND/.test(doc.status)?'danger':'muted'}>{t(doc.status)}</Chip>{doc.rejection_reason && <span className="review-reason" title={doc.rejection_reason}>{doc.rejection_reason}</span>}<span className="own-document-actions"><button type="button" className="ui-button ui-button-secondary" onClick={() => setPreview(doc)}>{t("View private document")}</button>{library&&(code&&code!==flow&&evidencePath?<Link className="inline-link" to={evidencePath(code)+'#own-documents-heading'}>{t("Manage ")}{code==='OWNER'?t('Owner'):t('Driver')}{t(" evidence")}</Link>:<button type="button" className="inline-link" onClick={()=>setLibrary(false)}>{t("Manage in this evidence flow")}</button>)}</span></article>})}
    </div>}
    {!uploading&&<div className="flow-actions">{rows.pager}{items && (page>1||hasNext) && <nav className="flow-pager" aria-label={t("Your document pages")}><button type="button" className="ui-button ui-button-secondary" disabled={loading || page === 1} onClick={() => load(page - 1)}>{t("Previous")}</button><span>{t("Page ")}{page}</span><button type="button" className="ui-button ui-button-secondary" disabled={loading || !hasNext} onClick={() => load(page + 1)}>{t("Next")}</button></nav>}{error && <button type="button" className="ui-button ui-button-secondary" disabled={loading} onClick={() => load(page)}>{t("Reload your documents")}</button>}</div>}
    {preview && <PrivateDocumentPreview key={preview.id} document={preview} onClose={() => setPreview(null)}/>}
  </section>
}
