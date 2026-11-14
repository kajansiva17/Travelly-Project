import { t } from '../i18n/language.js'
import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { ErrorNotice } from './components'
import {codeLabel} from '../i18n/codeLabels.js'

export default function PrivateDocumentPreview({ document, onClose, onDenied }) {
  const [blob, setBlob] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => {
    let cancelled = false, url
    api(`/documents/${document.id}/file`, { binary: true }).then(file => {
      if (cancelled) return
      url = URL.createObjectURL(file); setBlob({ url, type: file.type })
    }).catch(err => { if (!cancelled) { setError(err); if ([401, 403].includes(err.status)) onDenied?.(err) } })
    return () => { cancelled = true; if (url) URL.revokeObjectURL(url) }
  }, [document.id, onDenied])
  return <section className="review-preview" aria-label={t("Private document preview")}>
    <div className="review-panel-heading"><h3>{codeLabel(document.document_type)}</h3><button type="button" className="button outline" onClick={onClose}>{t("Close preview")}</button></div>
    <ErrorNotice error={error}/>
    {!blob && !error && <p role="status">{t("Loading protected document…")}</p>}
    {blob && (blob.type === 'application/pdf' ? <iframe src={blob.url} title={t("Private PDF evidence")}/> : <img src={blob.url} alt={t("Private application evidence")}/>)}
    <p>{t("Private evidence. Access is checked on every fetch.")}</p>
  </section>
}
