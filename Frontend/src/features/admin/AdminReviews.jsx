import { useEffect, useState } from 'react'
import { t } from '../../i18n/language.js'
import { api } from '../../services/api'
import { Header, ErrorNotice } from '../../components/components'
import { FlowShell } from '../booking/flow/FlowParts'
import { Button, FormField } from '../../components/ui'
import Chip from '../../components/ui/Chip'
import { displayTime } from '../../hooks/workspaceData'
import { stars } from '../trips/RateTrip'

const post = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body) })

function HideBox({ review, onDone, onCancel }) {
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  async function send(event) {
    event.preventDefault()
    setBusy(true); setError(null)
    try { await post(`/admin/reviews/${review.id}/hide`, { note: note.trim() }); onDone() } catch (failure) { setError(failure) } finally { setBusy(false) }
  }
  return <form className="flow-fields" onSubmit={send}>
    <ErrorNotice error={error}/>
    <FormField label={t('Reason for hiding')}>{({ id }) => <textarea id={id} rows={2} maxLength={300} value={note} onChange={event => setNote(event.target.value)}/>}</FormField>
    <div className="flow-actions"><Button type="submit" disabled={busy || !note.trim()}>{t('Hide review')}</Button><Button type="button" variant="secondary" onClick={onCancel}>{t('Cancel')}</Button></div>
  </form>
}

/* Admin > Reviews: every Passenger review, newest first. A hidden review drops out of the averages and the Owner's list. */
export default function AdminReviews() {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [hiding, setHiding] = useState('')
  const [onlyHidden, setOnlyHidden] = useState(false)
  const load = () => api('/admin/reviews', { cache: 'no-store' }).then(result => setItems(result.items || [])).catch(setError)
  useEffect(() => { load() }, [])
  async function show(review) {
    setError(null)
    try { await post(`/admin/reviews/${review.id}/unhide`, {}); load() } catch (failure) { setError(failure) }
  }
  const rows = (items || []).filter(item => !onlyHidden || item.hidden_at)
  return <><Header/><FlowShell heading={t('Reviews')} title={t('Trip reviews')} icon="star"
    info={t('Hide a review that breaks the rules. A hidden review is not counted in any rating and the Owner does not see it. You can show it again.')}>
    <ErrorNotice error={error}/>
    {!items && !error && <p role="status">{t('Loading…')}</p>}
    {items && <label><input type="checkbox" checked={onlyHidden} onChange={event => setOnlyHidden(event.target.checked)}/>{' '}{t('Only hidden reviews')}</label>}
    {items && !rows.length && <p className="flow-note" role="status">{t('No reviews yet.')}</p>}
    {rows.map(item => <article className="tk-row" key={item.id} style={{ display: 'block' }}>
      <div className="tk-row-main"><strong style={{ color: '#f5a623' }}>{stars(item.rating)}</strong>{' '}<strong>{item.vehicle}</strong>
        <span>{item.passenger ? item.passenger + ' · ' : ''}{item.trip_reference}{' · '}{displayTime(item.created_at)}{item.driver_rating ? ' · ' + t('Driver') + ' ' + stars(item.driver_rating) : ''}</span></div>
      {item.comment && <p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{item.comment}</p>}
      {item.reply && <p className="flow-note"><strong>{t('Owner reply')}{': '}</strong>{item.reply}</p>}
      {item.hidden_at && <p className="flow-note"><Chip tone="muted">{t('Hidden')}</Chip>{' '}{item.hidden_note}</p>}
      {hiding === item.id ? <HideBox review={item} onDone={() => { setHiding(''); load() }} onCancel={() => setHiding('')}/>
        : <div className="flow-actions">{item.hidden_at ? <Button type="button" variant="secondary" onClick={() => show(item)}>{t('Show again')}</Button>
          : <Button type="button" variant="secondary" onClick={() => setHiding(item.id)}>{t('Hide review')}</Button>}</div>}
    </article>)}
  </FlowShell></>
}
