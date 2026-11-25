import { t } from '../../i18n/language.js'
import { useEffect, useState } from 'react'
import { api } from '../../services/api'
import { Icon } from '../../components/components'
import { ChatPanel } from './CallContact'
import { BELL_OPENED, OPEN_CHAT } from './chatEvents'

const EVERY_MS = 15000   // gentle on the server; the open chat itself refreshes every 5 s

// The booking chat on top of any page of the workspace.
//  * A new message (an unread CHAT notice) shows a card like a Book now request, with Open chat / Later.
//  * Clicking a chat notice anywhere, or the bell while a chat message is waiting, opens that chat straight away.
export default function ChatHost({ enabled }) {
  const [openId, setOpenId] = useState('')
  const [unread, setUnread] = useState([])
  const [later, setLater] = useState({})

  useEffect(() => {
    const open = event => setOpenId(event.detail?.bookingId || '')
    window.addEventListener(OPEN_CHAT, open)
    return () => window.removeEventListener(OPEN_CHAT, open)
  }, [])

  useEffect(() => {
    if (!enabled) return undefined
    let alive = true
    const read = async () => {
      try {
        const result = await api('/notifications', { cache: 'no-store' })
        if (alive) setUnread((result?.items || []).filter(n => n.notification_type === 'CHAT' && !n.read_at && (n.booking_id || n.action_payload?.booking_id)))
      } catch { /* the next poll tries again */ }
    }
    read()
    const timer = setInterval(() => { if (!document.hidden) read() }, EVERY_MS)
    const visible = () => { if (!document.hidden) read() }
    document.addEventListener('visibilitychange', visible)
    return () => { alive = false; clearInterval(timer); document.removeEventListener('visibilitychange', visible) }
  }, [enabled, openId])

  useEffect(() => {
    const bell = () => { const first = unread[0]; if (first) setOpenId(first.booking_id || first.action_payload?.booking_id) }
    window.addEventListener(BELL_OPENED, bell)
    return () => window.removeEventListener(BELL_OPENED, bell)
  }, [unread])

  const waiting = openId ? [] : unread.filter(n => !later[n.id])
  return <>
    {waiting.length > 0 && <div className="ride-banner ride-banner-chat" role="alert" aria-live="assertive">
      {waiting.slice(0, 2).map(note => <div key={note.id} className="ride-banner-card">
        <div className="ride-banner-main">
          <strong className="ride-banner-title"><Icon name="chat" size={16}/>{t('New message')}</strong>
          <p>{note.body}</p>
        </div>
        <div className="live-actions">
          <button type="button" className="ui-button ui-button-primary" onClick={() => setOpenId(note.booking_id || note.action_payload?.booking_id)}>{t('Open chat')}</button>
          <button type="button" className="ui-button ui-button-secondary" onClick={() => setLater(current => ({ ...current, [note.id]: true }))}>{t('Later')}</button>
        </div>
      </div>)}
    </div>}
    {openId && <ChatPanel bookingId={openId} onClose={() => setOpenId('')}/>}
  </>
}
