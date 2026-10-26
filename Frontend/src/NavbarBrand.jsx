import React, { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

const brandAssets = {
  vehicles: '/images/brand/Front-Facing White Vehicle Lineup.png.png',
  face: '/images/brand/speedometer-face.png',
  needle: '/images/brand/speedometer-needle.png',
}

export default function NavbarBrand() {
  const location = useLocation()
  // A new history entry (including back/forward) gets its own single arrival
  // sweep. Form updates, resizing and ordinary pointer movement keep this key.
  return <AnimatedNavbarBrand key={location.key}/>
}

function AnimatedNavbarBrand() {
  const [ready, setReady] = useState(false)
  const [revving, setRevving] = useState(false)
  const busy = useRef(false)

  useEffect(() => {
    let active = true
    // Cached SVG <image> load events can arrive before React attaches handlers.
    // Decode from the shared browser cache instead; the vehicle artwork and
    // home link remain visible and usable while the meter becomes ready.
    Promise.all(Object.values(brandAssets).map(src => {
      const image = new Image()
      image.src = src
      return image.decode()
    })).then(() => { if (active) setReady(true) }).catch(() => { if (active) setReady(false) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (ready) replay()
  }, [ready])

  useEffect(() => {
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)')
    const stop = event => {
      if (event.matches) {
        busy.current = false
        setRevving(false)
      }
    }
    motion.addEventListener('change', stop)
    return () => motion.removeEventListener('change', stop)
  }, [])

  function replay() {
    if (!ready || busy.current || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    // Lock immediately, so rapid hover/focus events cannot interrupt a sweep.
    busy.current = true
    setRevving(true)
  }

  function pointerEnter(event) {
    if (event.pointerType === 'mouse' && window.matchMedia('(hover: hover) and (pointer: fine)').matches) replay()
  }

  function focus(event) {
    if (event.currentTarget.matches(':focus-visible') && !window.matchMedia('(pointer: coarse)').matches) replay()
  }

  return <Link className="brand" to="/" aria-label="Travelly home" onPointerEnter={pointerEnter} onFocus={focus}
    onAnimationEnd={event => {
      if (event.animationName === 'travelly-brand-rev') {
        busy.current = false
        setRevving(false)
      }
    }}>
    <span className={`brand-mark${ready ? ' is-ready' : ''}${revving ? ' is-revving' : ''}`} aria-hidden="true">
      <svg className="brand-speedometer" viewBox="0 0 1649 954" width="1649" height="954" focusable="false" aria-hidden="true">
        <image href={brandAssets.face} width="1649" height="954" onError={() => setReady(false)}/>
        {/* Align the source needle's (460.5, 752) hub with the face's (824.5, 884) pivot.
            The source image is scaled uniformly; CSS rotates only the needle. */}
        <g transform="translate(574.857 476.332) scale(0.5421126302)">
          <image className="brand-gauge-needle" href={brandAssets.needle} width="1536" height="1024" onError={() => setReady(false)}/>
        </g>
      </svg>
      <img className="brand-vehicles" src={brandAssets.vehicles} width="1912" height="823"
        alt="" loading="eager" fetchPriority="auto" decoding="async" onError={() => setReady(false)}/>
    </span>
    <span className="brand-wordmark">Travelly</span>
  </Link>
}
