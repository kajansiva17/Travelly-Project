import { t } from '../../i18n/language.js'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, clearSession } from '../../services/api'
import { ErrorNotice } from '../../components/components'
import { Button } from '../../components/ui'
import { usePaged, useRowCount } from '../booking/flow/FlowParts'
import { ConfirmForm } from './TwoFactorSettings'
import { blockerLines, canClose, closeBody } from './loginFlow'

/* Deactivate or delete the account (contract 03SV, section 2). The open business listed by GET /users/me/account-closure must be
   finished first: the buttons stay off while it exists. Success signs the person out (the server already ended every session). */
export default function CloseAccount({ hasPassword, twoFactorOn }) {
  const [status, setStatus] = useState(null), [error, setError] = useState(null), [action, setAction] = useState(null)   // null | 'deactivate' | 'delete'
  const lines = blockerLines(status?.blockers), rows = usePaged(lines, useRowCount(48))
  const load = () => api('/users/me/account-closure', { cache: 'no-store' }).then(r => { setStatus(r); setError(null) }).catch(setError)
  useEffect(() => { load() }, [])
  const days = status?.delete_after_days ?? 30
  async function close(body) {
    try {
      await api(action === 'delete' ? '/users/me/delete-request' : '/users/me/deactivate', { method: 'POST', body: JSON.stringify(closeBody({ ...body, hasPassword, password: body.password, twoFactorOn, code: body.code })) })
    } catch (err) {
      if (err.code === 'ACCOUNT_HAS_OPEN_ITEMS') { setAction(null); await load() }   // something became open since the check
      throw err
    }
    // The server already ended every session. End it here and load the landing page fresh, so the sign-in guard of this page cannot redirect to /login.
    clearSession('logout'); window.location.replace('/')
  }
  const ok = canClose(status)
  return <section className="tk-pane" aria-label={t('Close your account')}>
    <ErrorNotice error={error}/>
    {!status && !error ? <p role="status">{t('Loading…')}</p> : status && <>
      {ok ? <p className="tk-line">{t('Nothing is open on your account. You can deactivate or delete it.')}</p>
        : <><p className="tk-line is-warn" role="alert">{t('Finish or settle these first:')}</p>
          <div className="tk-rows">{rows.slice.map(line => <article className="tk-row tk-row-wrap" key={line.code}><div className="tk-row-main"><strong>{line.key ? t(line.key, line.params) : line.text}</strong></div>
            {line.path && <div className="tk-row-actions"><Link className="ui-button ui-button-secondary" to={line.path}>{t('Open')}</Link></div>}</article>)}</div></>}
      {action
        ? <ConfirmForm hasPassword={hasPassword} needCode={twoFactorOn} danger
            intro={action === 'delete' ? t('Your account is deactivated now and your personal data is removed after {value0} days. Signing in before then cancels the request.', { value0: days }) : t('Your account is deactivated and you are signed out everywhere. Sign in again any time to bring it back.')}
            submitLabel={action === 'delete' ? t('Yes, delete my account') : t('Yes, deactivate my account')} onSubmit={close} onCancel={() => setAction(null)}/>
        : <div className="flow-actions">{rows.pager || <span/>}<span className="tk-bar"><Button variant="secondary" disabled={!ok} onClick={() => setAction('deactivate')}>{t('Deactivate account')}</Button><Button disabled={!ok} onClick={() => setAction('delete')}>{t('Delete account')}</Button></span></div>}
    </>}
  </section>
}
