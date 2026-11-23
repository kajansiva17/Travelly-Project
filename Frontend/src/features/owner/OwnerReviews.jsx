import { useEffect, useState } from 'react'
import { t } from '../../i18n/language.js'
import { api } from '../../services/api'
import { Header, ErrorNotice } from '../../components/components'
import { FlowShell } from '../booking/flow/FlowParts'
import { Button, FormField, Select } from '../../components/ui'
import { displayTime } from '../../hooks/workspaceData'
import { stars } from '../trips/RateTrip'

function ReplyBox({ review, onDone, onCancel }) {
  const [text, setText] = useState(review.reply || '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  async function send(event) {
    event.preventDefault()
    setBusy(true); setError(null)
    try { await api(`/reviews/${review.id}/reply`, { method: 'POST', body: JSON.stringify({ text: text.trim() }) }); onDone() } catch (failure) { setError(failure) } finally { setBusy(false) }
  }
  return <form className="flow-fields" onSubmit={send}>
    <ErrorNotice error={error}/>
    <FormField label={t('Your reply')}>{({ id }) => <textarea id={id} rows={2} maxLength={300} value={text} onChange={event => setText(event.target.value)}/>}</FormField>
    <div className="flow-actions"><Button type="submit" disabled={busy || !text.trim()}>{busy ? t('Sending…') : t('Send reply')}</Button>
      {onCancel && <Button type="button" variant="secondary" onClick={onCancel}>{t('Cancel')}</Button>}</div>
  </form>
}

function Answer({ review, onDone }) {
  const [editing, setEditing] = useState(false)
  const [error, setError] = useState(null)
  async function remove() {
    setError(null)
    try { await api(`/reviews/${review.id}/reply`, { method: 'DELETE', body: '{}' }); onDone() } catch (failure) { setError(failure) }
  }
  if (!review.reply) return <ReplyBox review={review} onDone={onDone}/>
  if (editing) return <ReplyBox review={review} onDone={() => { setEditing(false); onDone() }} onCancel={() => setEditing(false)}/>
  return <>
    <p className="flow-note"><strong>{t('Your reply')}{': '}</strong>{review.reply}</p>
    <ErrorNotice error={error}/>
    <div className="flow-actions">
      <Button type="button" variant="secondary" onClick={() => setEditing(true)}>{t('Edit reply')}</Button>
      <Button type="button" variant="secondary" onClick={remove}>{t('Delete reply')}</Button>
    </div>
  </>
}

/* Sidebar > Reviews (Owner): what Passengers rated after their trips, per vehicle; the Owner may answer each review once. */
export default function OwnerReviews() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [vehicle, setVehicle] = useState('')
  const load = () => api('/owners/me/reviews', { cache: 'no-store' }).then(setData).catch(setError)
  useEffect(() => { load() }, [])
  const items = (data?.items || []).filter(item => !vehicle || item.vehicle_id === vehicle)
  return <><Header/><FlowShell heading={t('Reviews')} title={t('What Passengers say about your vehicles')} icon="users"
    info={t('Passengers rate a trip once it has finished. You can answer each review, and change or remove your reply later.')}>
    <ErrorNotice error={error}/>
    {!data && !error && <p role="status">{t('Loading…')}</p>}
    {data && !data.count && <p className="flow-note" role="status">{t('No reviews yet.')}</p>}
    {data && data.count > 0 && <>
      <p><strong style={{ fontSize: 22, color: '#f5a623' }}>{stars(Math.round(Number(data.average)))}</strong>{' '}<strong>{data.average}</strong>{' · '}{t('{value0} reviews', { value0: data.count })}</p>
      <FormField label={t('Vehicle')}>
        {({ id }) => <Select id={id} value={vehicle} onChange={event => setVehicle(event.target.value)}><option value="">{t('All vehicles')}</option>
          {data.vehicles.map(item => <option key={item.id} value={item.id}>{item.registration}{' · '}{item.average}{' ('}{item.count}{')'}</option>)}</Select>}
      </FormField>
      {items.map(item => <article className="tk-row" key={item.id} style={{ display: 'block' }}>
        <div className="tk-row-main"><strong style={{ color: '#f5a623' }}>{stars(item.rating)}</strong>{' '}<strong>{item.vehicle}</strong>
          <span>{item.passenger ? item.passenger + ' · ' : ''}{item.trip_reference}{' · '}{displayTime(item.created_at)}{item.driver_rating ? ' · ' + t('Driver') + ' ' + stars(item.driver_rating) : ''}</span></div>
        {item.comment && <p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{item.comment}</p>}
        {item.edited_at && <p className="flow-note">{t('Edited by the Passenger')}</p>}
        <Answer review={item} onDone={load}/>
      </article>)}
    </>}
  </FlowShell></>
}
