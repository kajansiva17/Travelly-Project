import { t, getLanguage } from '../../i18n/language.js'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../services/api'
import { Icon } from '../../components/components'
import { openChat } from '../trips/chatEvents'
import { isExpired, isRoadAlertNotice, noticeBookingId } from './notices'

// The bell opens this list: the latest notifications, newest first. A road alert is worded in the language of the page, a chat message opens the chat.
const SHOWN = 15
const icons = { ROAD_ALERT: 'alert', CHAT: 'chat' }

function wording(note) {
  const payload = note.action_payload || {}
  if (isRoadAlertNotice(note)) {
    const language = getLanguage(), heard = payload.speak_all?.[language]
    const km = typeof payload.distance_km === 'number' ? ' (' + t('{value0} km', { value0: payload.distance_km }) + ')' : ''
    return { title: payload.titles?.[language] || note.title, body: heard ? heard + km : note.body }
  }
  return { title: note.title, body: note.body }
}

function when(value) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString([], { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export default function NotificationPanel({ role, seeAll, onClose }) {
  const [state, setState] = useState({ items: null, error: null })

  useEffect(() => {
    let alive = true
    api('/notifications', { cache: 'no-store' }).then(result => { if (alive) setState({ items: (result.items || []).slice(0, SHOWN), error: null }) }).catch(error => { if (alive) setState({ items: [], error }) })
    return () => { alive = false }
  }, [])
  useEffect(() => {
    const key = event => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [onClose])

  const linkOf = note => {
    if (isRoadAlertNotice(note)) return note.trip_id && role === 'DRIVER' ? '/driver/trips/' + note.trip_id + '/live' : note.trip_id && role === 'OWNER' ? '/owner/driving/trips/' + note.trip_id : null
    // An Admin notice about a departure (an Owner cannot run it) opens the Needs attention list where the Admin decides.
    if (role === 'ADMIN' && note.notification_type === 'ADMIN_ACTION' && note.action_payload?.scheduled_trip_id) return '/admin/services-routes?tab=attention'
    return seeAll
  }
  const row = note => {
    const { title, body } = wording(note), expired = isExpired(note), chat = note.notification_type === 'CHAT' && noticeBookingId(note)
    const inside = <><span className="np-icon"><Icon name={icons[note.notification_type] || 'bell'} size={20}/></span>
      <span className="np-text"><strong>{title}{isRoadAlertNotice(note) && expired && <> · {t('Expired')}</>}</strong><span>{body}</span><small>{when(note.created_at)}</small></span></>
    const className = 'np-item' + (expired ? ' is-expired' : '')
    if (chat) return <li key={note.id}><button type="button" className={className} onClick={() => { onClose(); openChat(noticeBookingId(note)) }}>{inside}</button></li>
    const to = linkOf(note)
    return <li key={note.id}>{to ? <Link className={className} to={to} onClick={onClose}>{inside}</Link> : <div className={className}>{inside}</div>}</li>
  }

  return <div className="np-backdrop" role="presentation" onClick={onClose}>
    <section className="np-panel" role="dialog" aria-label={t('Notifications')} onClick={event => event.stopPropagation()}>
      <header className="np-head"><strong>{t('Notifications')}</strong><button type="button" className="np-close" aria-label={t('Close')} onClick={onClose}><Icon name="close" size={20}/></button></header>
      <ul className="np-list">
        {state.items === null && <li className="np-empty" role="status">{t('Loading…')}</li>}
        {state.items && !state.items.length && <li className="np-empty" role="status">{state.error ? t('Unable to load this information') : t('No notifications yet.')}</li>}
        {state.items && state.items.map(row)}
      </ul>
      <footer className="np-foot"><Link className="ui-button ui-button-secondary" to={seeAll} onClick={onClose}>{t('See all')}</Link></footer>
    </section>
  </div>
}
