import React, { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import { ErrorNotice } from './components'
import PrivateDocumentPreview from './PrivateDocumentPreview'
import DocumentUploadForm from './DocumentUploadForm'

export default function OwnDocuments({ user }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [preview, setPreview] = useState(null)
  const [page, setPage] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const load = useCallback(async () => {
    setError(null); setItems(null)
    try { const result = await api(`/documents?user_id=${user.id}&page=${page}&page_size=20`); setItems(result.items); setHasNext(result.has_next) }
    catch (err) { setError(err) }
  }, [user.id, page])
  useEffect(() => { load() }, [load])
  return <section className="review-panel" aria-labelledby="own-documents-heading">
    <h2 id="own-documents-heading">Your private application documents</h2>
    <p>Correct a reviewed file by submitting a new document of the same type. Your earlier files and reasons are retained. Replacing a file does not reinstate a suspended role.</p>
    <DocumentUploadForm user={user} onUploaded={load}/>
    <ErrorNotice error={error}/>
    {items === null && !error && <p role="status">Loading your documents…</p>}
    {items?.length === 0 && <p>No private documents submitted yet.</p>}
    {items?.map(doc => <article className="review-document" key={doc.id}><h3>{doc.document_type.replaceAll('_', ' ')}</h3><p>{doc.status}</p>{doc.rejection_reason && <p className="review-reason">{doc.rejection_reason}</p>}<button className="button outline" onClick={() => setPreview(doc)}>View private document</button></article>)}
    {items && <nav className="review-pagination" aria-label="Your document pages"><button className="button outline" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page}</span><button className="button outline" disabled={!hasNext} onClick={() => setPage(page + 1)}>Next</button></nav>}
    {preview && <PrivateDocumentPreview key={preview.id} document={preview} onClose={() => setPreview(null)}/>}
    {error && <button className="button outline" onClick={load}>Reload your documents</button>}
  </section>
}
