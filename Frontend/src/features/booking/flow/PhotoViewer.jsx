import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { t } from '../../../i18n/language.js'
import { Icon } from '../../../components/components'
import { mediaUrl } from '../../../services/api'

/* Every picture of a vehicle that a Passenger may see: the profile picture first, then the approved
   exterior and interior photos the Owner uploaded (the search result already carries them). */
export function vehicleImages(vehicle) {
  const out = [], seen = new Set()
  const add = (image) => { if (image.src && !seen.has(image.src)) { seen.add(image.src); out.push(image) } }
  const profile = vehicle?.profile_image_url
  if (profile) add({ src: profile, cover: profile, thumb: profile, label: '' })
  for (const photo of vehicle?.photos || []) {
    if (profile && photo.id && profile.includes(photo.id)) continue
    const sizes = [...(photo.variants || [])].sort((a, b) => a.width - b.width)
    if (!sizes.length) continue
    const full = sizes[sizes.length - 1], cover = sizes.find(v => v.width >= 640) || full
    add({ src: mediaUrl(full.url), cover: mediaUrl(cover.url), thumb: mediaUrl(sizes[0].url), label: photo.category === 'INTERIOR' ? 'Interior' : photo.category === 'EXTERIOR' ? 'Exterior' : '' })
  }
  return out
}

/* Full-screen viewer: arrows, swipe, keyboard and a thumbnail strip. */
export function PhotoViewer({ images, start = 0, title, onClose }) {
  const [i, setI] = useState(start), touch = useRef(null), n = images.length
  const go = d => setI(v => (v + d + n) % n)
  useEffect(() => {
    const key = e => { if (e.key === 'Escape') onClose(); else if (e.key === 'ArrowRight') go(1); else if (e.key === 'ArrowLeft') go(-1) }
    window.addEventListener('keydown', key)
    const before = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { window.removeEventListener('keydown', key); document.body.style.overflow = before }
  }, [])
  const image = images[i]
  const swipe = e => { if (touch.current == null) return; const dx = e.changedTouches[0].clientX - touch.current; touch.current = null; if (Math.abs(dx) > 50) go(dx < 0 ? 1 : -1) }
  return createPortal(
    <div className="pv" role="dialog" aria-modal="true" aria-label={title} onTouchStart={e => { touch.current = e.touches[0].clientX }} onTouchEnd={swipe}>
      <header className="pv-bar">
        <strong>{title}</strong>
        <span>{t('Photo {value0} of {value1}', { value0: i + 1, value1: n })}</span>
        <button type="button" className="pv-close" onClick={onClose} aria-label={t('Close photos')}><Icon name="close" size={22} aria-hidden="true"/></button>
      </header>
      <div className="pv-stage" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
        {n > 1 && <button type="button" className="pv-nav pv-prev" onClick={() => go(-1)} aria-label={t('Previous photo')}><Icon name="arrow" size={22} className="ui-back-arrow" aria-hidden="true"/></button>}
        <img src={image.src} alt={image.label ? `${title} · ${t(image.label)}` : title} referrerPolicy="no-referrer" draggable="false"/>
        {n > 1 && <button type="button" className="pv-nav pv-next" onClick={() => go(1)} aria-label={t('Next photo')}><Icon name="arrow" size={22} aria-hidden="true"/></button>}
      </div>
      {image.label && <p className="pv-label">{t(image.label)}</p>}
      {n > 1 && <ul className="pv-thumbs">{images.map((p, k) => <li key={p.src}><button type="button" className={k === i ? 'is-on' : ''} onClick={() => setI(k)} aria-label={t('Photo {value0} of {value1}', { value0: k + 1, value1: n })} aria-current={k === i}><img src={p.thumb} alt="" referrerPolicy="no-referrer" loading="lazy"/></button></li>)}</ul>}
    </div>, document.body)
}
