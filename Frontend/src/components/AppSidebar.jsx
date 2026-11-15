import { t } from '../i18n/language.js'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import AiAssistant from '../features/ai/AiAssistant'
import { ErrorNotice, Icon } from './components'
import { activeMenuItem, canDriveAsOwner, travelHome, workspaceMenu } from '../routes/workspaceRoutes'
import { useWorkspace } from '../context/workspaceContext'

/* Single white-glass sidebar for all four roles (skin: styles/app-sidebar.css).
   Layout: the menu list scrolls; the bottom block (Settings, Profile,
   Travel & Booking, Logout) is always pinned and visible, also at browser zoom.
   Only the role's menu items differ; the design is identical. */
export default function AppSidebar({ role, info, authorized, pathname, search, mobile = false, busy = false, onSignOut, logoutError, onClose }) {
  const workspace = useWorkspace(), [aiOpen, setAiOpen] = useState(false)
  const travelPath = travelHome(role)
  const menu = workspaceMenu(role, { driving: role === 'OWNER' && canDriveAsOwner(workspace?.user) })
  // Owner: Travel & booking is a normal menu entry (contract 03W order). Other roles keep it in the pinned bottom block.
  const inMenu = menu.some(item => item.travel)
  const main = menu.filter(item => !item.bottom && (inMenu || item.path !== travelPath))
  const bottom = menu.filter(item => item.bottom)
  const travelActive = pathname.startsWith(info.prefix + '/personal/') || pathname.startsWith(info.prefix + '/travel') || (role === 'PASSENGER' && (pathname.startsWith('/travel/') || pathname === '/hire' || pathname.startsWith('/vehicles/')))
  // A booking opened from a list or a notification (/bookings/:id) keeps its own list highlighted, so the person knows where they are.
  const detailHome = pathname.startsWith('/bookings/') ? ({ OWNER: '/owner/bookings', DRIVER: info.prefix + '/assignments' })[role] : null
  const current = (detailHome && main.find(item => item.path === detailHome)) || (inMenu && travelActive ? main.find(item => item.travel) : activeMenuItem([...main, ...bottom], pathname, search))
  const link = item => {
    const active = item === current
    if (item.action === 'ai') return <button key={item.label} type="button" className="app-sidebar-link" onClick={() => { setAiOpen(true); onClose?.() }}>
      <Icon name={item.icon} size={20}/><span>{t(item.label)}</span>
    </button>
    return <Link key={item.label} to={item.path} className={'app-sidebar-link' + (active ? ' is-active' : '')} aria-current={active ? 'page' : undefined}>
      <Icon name={item.icon} size={20}/><span>{t(item.label)}</span>
    </Link>
  }
  return <>
    {mobile && <div className="app-sidebar-title">
      <strong>{t(info.label)}</strong>
      <button className="workspace-icon-button" aria-label={t('Close workspace navigation')} onClick={onClose}><Icon name="close"/></button>
    </div>}
    <nav aria-label={t('{value0} sidebar', { value0: t(info.label) })} className="app-sidebar-nav">
      <div className="app-sidebar-menu">{authorized && main.map(link)}</div>
      <div className="app-sidebar-bottom">
        {authorized && bottom.map(link)}
        {!inMenu && <Link to={travelPath} className={'app-sidebar-link' + (travelActive ? ' is-active' : '')} aria-current={travelActive ? 'page' : undefined}>
          <Icon name="plane" size={20}/><span>{t('Travel & booking')}</span>
        </Link>}
        <button type="button" className="app-sidebar-link" disabled={busy} onClick={onSignOut}>
          <Icon name="exit" size={20}/><span>{busy ? t('Signing out...') : t('Logout')}</span>
        </button>
        {mobile && <ErrorNotice error={logoutError}/>}
      </div>
    </nav>
    {aiOpen && <AiAssistant initialTab="search" onClose={() => setAiOpen(false)}/>}
  </>
}
