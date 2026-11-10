import { t } from '../i18n/language.js'
import React from 'react'
import { Link } from 'react-router-dom'
import { ErrorNotice, Icon } from './components'
import { activeMenuItem, personalHirePath, workspaceMenu } from '../routes/workspaceRoutes'

/* Single white-glass sidebar for all four roles (skin: styles/app-sidebar.css).
   Layout: the menu list scrolls; the bottom block (Settings, Profile,
   Travel & Booking, Logout) is always pinned and visible, also at browser zoom.
   Only the role's menu items differ; the design is identical. */
export default function AppSidebar({ role, info, authorized, pathname, search, mobile = false, busy = false, onSignOut, logoutError, onClose }) {
  const travelPath = personalHirePath(role)
  const menu = workspaceMenu(role)
  // Travel & Booking lives in the shared bottom block for every role.
  const main = menu.filter(item => !item.bottom && item.path !== travelPath)
  const bottom = menu.filter(item => item.bottom)
  const travelActive = pathname.startsWith(info.prefix + '/personal/') || (role === 'PASSENGER' && (pathname.startsWith('/travel/') || pathname === '/hire' || pathname.startsWith('/vehicles/')))
  const current = activeMenuItem([...main, ...bottom], pathname, search)
  const link = item => {
    const active = item === current
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
        <Link to={travelPath} className={'app-sidebar-link' + (travelActive ? ' is-active' : '')} aria-current={travelActive ? 'page' : undefined}>
          <Icon name="plane" size={20}/><span>{t('Travel & Booking')}</span>
        </Link>
        <button type="button" className="app-sidebar-link" disabled={busy} onClick={onSignOut}>
          <Icon name="exit" size={20}/><span>{busy ? t('Signing out...') : t('Logout')}</span>
        </button>
        {mobile && <ErrorNotice error={logoutError}/>}
      </div>
    </nav>
  </>
}
