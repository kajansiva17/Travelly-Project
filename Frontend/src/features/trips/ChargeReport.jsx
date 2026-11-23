import { useCallback, useEffect, useState } from 'react'
import { t } from '../../i18n/language.js'
import { api } from '../../services/api'
import { ErrorNotice } from '../../components/components'
import { Button, FormField } from '../../components/ui'

const money = value => Number(value).toFixed(2)

// Finished Book now return with a waiting charge. The Passenger may report the charge (a reason is optional, payment is never held up);
// the Owner of the vehicle then keeps the charge or lowers it. Hidden when there is nothing to show.
export default function ChargeReport({ tripId }) {
  const [state, setState] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [reason, setReason] = useState('')
  const [open, setOpen] = useState(false)
  const [lowering, setLowering] = useState(false)
  const [newCharge, setNewCharge] = useState('')
  const [note, setNote] = useState('')
  const load = useCallback(() => api(`/trips/${encodeURIComponent(tripId)}/charge-report`, { cache: 'no-store' }).then(setState).catch(setError), [tripId])
  useEffect(() => { load() }, [load])

  async function run(path, body) {
    setBusy(true); setError(null)
    try { await api(path, { method: 'POST', body: JSON.stringify(body) }); setOpen(false); setLowering(false); await load() }
    catch (failure) { setError(failure); await load() }
    finally { setBusy(false) }
  }

  if (error && !state) return <ErrorNotice error={error}/>
  if (!state || (!state.report && !state.can_report)) return null
  const report = state.report
  const canAnswer = state.is_owner && report?.status === 'OPEN'

  return <section className="flow-wizard-form" aria-label={t('Waiting charge')} role="status">
    <strong>{t('Waiting charge')}{': LKR '}{money(report ? report.charge : state.charge)}</strong>
    <ErrorNotice error={error}/>
    {!report && state.can_report && <>
      <p className="flow-note">{t('If the waiting charge looks wrong, you can report it. Payment is not held up.')}</p>
      {!open && <div className="flow-actions"><Button type="button" variant="secondary" onClick={() => setOpen(true)}>{t('Report this charge')}</Button></div>}
      {open && <>
        <FormField label={t('What was wrong? (optional)')}>
          {({ id }) => <textarea id={id} rows={2} maxLength={300} value={reason} onChange={event => setReason(event.target.value)}/>}
        </FormField>
        <div className="flow-actions">
          <Button type="button" disabled={busy} onClick={() => run(`/trips/${encodeURIComponent(tripId)}/charge-report`, { reason: reason.trim() || null })}>{t('Send report')}</Button>
          <Button type="button" variant="secondary" onClick={() => setOpen(false)}>{t('Cancel')}</Button>
        </div>
      </>}
    </>}
    {report && <>
      {report.reason && <p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{report.reason}</p>}
      {report.status === 'OPEN' && <p className="flow-note">{state.is_owner ? t('The Passenger reported this charge. Keep it or lower it.') : t('Reported. The Owner will look at it. If there is no answer, ask Support.')}</p>}
      {report.status === 'KEPT' && <p className="flow-note">{t('The Owner kept the charge.')}</p>}
      {report.status === 'REDUCED' && <p className="flow-note">{t('The Owner lowered the charge to LKR {value0}.', { value0: money(report.new_charge) })}{report.refund_due ? ' ' + t('LKR {value0} will be refunded.', { value0: money(report.refund_due) }) : ''}</p>}
      {report.owner_note && <p className="flow-note">{t('Owner note')}{': '}{report.owner_note}</p>}
    </>}
    {canAnswer && <>
      {lowering && <>
        <FormField label={t('New waiting charge (LKR)')}>
          {({ id }) => <input id={id} inputMode="decimal" value={newCharge} onChange={event => setNewCharge(event.target.value)}/>}
        </FormField>
      </>}
      <FormField label={t('Note (optional)')}>
        {({ id }) => <textarea id={id} rows={2} maxLength={300} value={note} onChange={event => setNote(event.target.value)}/>}
      </FormField>
      <div className="flow-actions">
        <Button type="button" disabled={busy} onClick={() => run(`/charge-reports/${report.id}/answer`, { keep: true, note: note.trim() || null })}>{t('Keep the charge')}</Button>
        {!lowering && <Button type="button" variant="secondary" onClick={() => setLowering(true)}>{t('Lower the charge')}</Button>}
        {lowering && <Button type="button" variant="secondary" disabled={busy || newCharge.trim() === ''} onClick={() => run(`/charge-reports/${report.id}/answer`, { keep: false, new_charge: newCharge.trim(), note: note.trim() || null })}>{t('Save lower charge')}</Button>}
      </div>
    </>}
  </section>
}
