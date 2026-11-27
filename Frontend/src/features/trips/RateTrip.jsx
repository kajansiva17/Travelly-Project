import { useEffect, useState } from 'react'
import { t } from '../../i18n/language.js'
import { api } from '../../services/api'
import { ErrorNotice, Icon } from '../../components/components'
import { Button, FormField } from '../../components/ui'

export const stars = count => '★'.repeat(count) + '☆'.repeat(5 - count)

function Stars({ value, onChange, label }) {
  return <div role="group" aria-label={label} style={{ display: 'flex', gap: 4 }}>
    {[1, 2, 3, 4, 5].map(number => <button key={number} type="button" aria-pressed={value === number} aria-label={t('{value0} out of 5', { value0: number })} onClick={() => onChange(number)}
      style={{ background: 'none', border: 0, cursor: 'pointer', fontSize: 28, lineHeight: 1, color: number <= value ? '#f5a623' : 'inherit', opacity: number <= value ? 1 : .45 }}>{number <= value ? '★' : '☆'}</button>)}
  </div>
}

/* Shown on a finished booking: the Passenger rates the trip once (vehicle and service, and the Driver when there was one) and may write a comment. */
export default function RateTrip({ tripId }) {
  const [state, setState] = useState(null)
  const [error, setError] = useState(null)
  const [rating, setRating] = useState(0)
  const [driver, setDriver] = useState(0)
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [editing, setEditing] = useState(false)
  const [confirm, setConfirm] = useState(false)
  const load = () => api(`/trips/${tripId}/review`, { cache: 'no-store' }).then(setState).catch(setError)
  useEffect(() => { load() }, [tripId])

  async function submit(event) {
    event.preventDefault()
    setBusy(true); setError(null)
    try {
      await api(`/trips/${tripId}/review`, { method: editing ? 'PUT' : 'POST', body: JSON.stringify({ rating, driver_rating: driver || null, comment: comment.trim() || null }) })
      setEditing(false); await load()
    } catch (failure) { setError(failure); await load() }
    finally { setBusy(false) }
  }

  function edit() {
    setRating(state.review.rating); setDriver(state.review.driver_rating || 0); setComment(state.review.comment || ''); setError(null); setConfirm(false); setEditing(true)
  }

  async function remove() {
    if (!confirm) { setConfirm(true); return }
    setBusy(true); setError(null)
    try { await api(`/trips/${tripId}/review`, { method: 'DELETE', body: '{}' }); setConfirm(false); setRating(0); setDriver(0); setComment(''); await load() } catch (failure) { setError(failure); await load() }
    finally { setBusy(false) }
  }

  if (error && !state) return <ErrorNotice error={error}/>
  if (!state || (!state.review && !state.can_review)) return null
  // after a delete the same trip can be reviewed again (state.can_review is true and there is no review)
  if (state.review && !editing) {
    const review = state.review
    return <section className="bc-card rt-card" aria-label={t('Your review')}>
      <strong className="rt-title"><Icon name="star" size={18}/>{t('Your review')}</strong>
      <p aria-label={t('{value0} out of 5', { value0: review.rating })} style={{ margin: 0, fontSize: 22, color: '#f5a623' }}>{stars(review.rating)}</p>
      {review.driver_rating && <p className="flow-note">{t('Driver')}{': '}{stars(review.driver_rating)}</p>}
      {review.comment && <p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{review.comment}</p>}
      {review.edited_at && <p className="flow-note">{t('Edited')}</p>}
      {review.reply && <p className="flow-note"><strong>{t('Reply from the Owner')}{': '}</strong>{review.reply}</p>}
      <ErrorNotice error={error}/>
      {state.can_edit && <>
        <p className="flow-note">{t('You can change or delete your review for {value0} days after writing it.', { value0: state.edit_days })}</p>
        <div className="flow-actions">
          <Button type="button" variant="secondary" onClick={edit} disabled={busy}>{t('Edit review')}</Button>
          <Button type="button" variant="secondary" onClick={remove} disabled={busy}>{confirm ? t('Tap again to delete') : t('Delete review')}</Button>
        </div>
      </>}
    </section>
  }
  return <form className="bc-card rt-card" onSubmit={submit}>
    <strong className="rt-title"><Icon name="star" size={18}/>{editing ? t('Edit your review') : t('Rate this trip')}</strong>
    <ErrorNotice error={error}/>
    <div className="rt-rates"><FormField label={t('How was the vehicle and the service?')}>{() => <Stars value={rating} onChange={setRating} label={t('How was the vehicle and the service?')}/>}</FormField>
    {state.has_driver && <FormField label={t('How was the Driver?')}>{() => <Stars value={driver} onChange={setDriver} label={t('How was the Driver?')}/>}</FormField>}</div>
    <FormField label={t('Comment (optional)')}>
      {({ id }) => <textarea id={id} rows={2} maxLength={500} value={comment} onChange={event => setComment(event.target.value)}/>}
    </FormField>
    <div className="flow-actions"><Button type="submit" disabled={busy || !rating}>{busy ? t('Submitting…') : editing ? t('Save changes') : t('Submit review')}</Button>
      {editing && <Button type="button" variant="secondary" onClick={() => setEditing(false)}>{t('Cancel')}</Button>}</div>
  </form>
}
