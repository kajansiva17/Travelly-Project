import React, { useEffect, useState } from 'react'
import { api } from './api'
import { ErrorNotice } from './components'

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
  return <section className="review-preview" aria-label="Private document preview">
    <div className="review-panel-heading"><h3>{document.document_type.replaceAll('_', ' ')}</h3><button type="button" className="button outline" onClick={onClose}>Close preview</button></div>
    <ErrorNotice error={error}/>
    {!blob && !error && <p role="status">Loading protected document…</p>}
    {blob && (blob.type === 'application/pdf' ? <iframe src={blob.url} title="Private PDF evidence"/> : <img src={blob.url} alt="Private application evidence"/>)}
    <p>Private evidence. Access is checked on every fetch.</p>
  </section>
}
