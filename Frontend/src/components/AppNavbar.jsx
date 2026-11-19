import { t } from '../i18n/language.js'
import { Link } from 'react-router-dom'
import { Icon } from './components'
import DashboardAvatar from './DashboardAvatar'
import {unreadBadge} from '../features/notifications/unread.js'

/* Right-hand items of the single Travelly navbar (owner design). Every role
   renders the same pieces in the same order: language, Travel Reels,
   notifications, account. Only the labels and link targets differ per role.
   The skin lives in styles/app-navbar.css. */

export function NavbarReels({ to }) {
  if (to) return <Link className="workspace-reels app-nav-reels" to={to} aria-label={t('Travel Reels')}><Icon name="video" size={22}/><span>{t('Travel Reels')}</span></Link>
  return <span className="workspace-reels app-nav-reels" aria-label={t('Travel Reels unavailable')}><Icon name="video" size={22}/><span>{t('Travel Reels')}</span></span>
}

export function NavbarBell({ to, label, unreadCount=0, onOpen }) {
  const badge=unreadBadge(unreadCount)
  const accessible=badge?t('{value0}. {value1} unread notifications',{value0:label,value1:unreadCount}):label
  return <Link className="admin-notifications app-nav-bell" to={to} aria-label={accessible} onClick={onOpen}>
    <Icon name="bell" size={25}/>
    {badge&&<span className="app-nav-bell-badge" aria-hidden="true">{badge}</span>}
  </Link>
}

/* Avatar + name: a plain link to the role's profile page (no menu). */
export function NavbarProfile({ user, roleLabel, profileTo }) {
  const name = user.display_name || user.full_name
  return <Link className="workspace-profile app-nav-profile" to={profileTo} aria-label={t('{value0}, {value1} workspace', { value0: name, value1: roleLabel })}>
    <DashboardAvatar name={name} url={user.profile_image_url}/>
    <span className="workspace-profile-name"><strong>{name}</strong><small>{roleLabel}</small></span>
  </Link>
}
