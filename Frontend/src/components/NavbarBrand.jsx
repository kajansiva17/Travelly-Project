import { t } from '../i18n/language.js'
import React, { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'

const brandAssets = '/images/travelly/branding/approved-2026-11-07/'
const dial = brandAssets + 'meter-dial.png'
const needle = brandAssets + 'meter-needle.png'
export const NEEDLE_REST = -132
export const NEEDLE_PEAK = 18

// Retain only decorative motion across navigation, when the header remounts.
let sweepStartedAt = -Infinity
let motion = { angle: NEEDLE_REST, velocity: 0 }
const sweepListeners = new Set()

export function sweepNavbarNeedle() {
  sweepStartedAt = performance.now()
  sweepListeners.forEach(wake => wake())
}

export default function TravellyBrand({ needleAngle = NEEDLE_REST }) {
  const needleElement = useRef(null)
  const target = useRef(needleAngle)
  const wakeMotion = useRef(null)
  const initialAngle = useRef(null)
  if (initialAngle.current === null) {
    initialAngle.current = performance.now() - sweepStartedAt < 1500 ? motion.angle : NEEDLE_REST
  }

  useEffect(() => {
    target.current = needleAngle
    wakeMotion.current?.()
  }, [needleAngle])

  useEffect(() => {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
    let frame = null
    let previousTime = null
    let angle = initialAngle.current
    let velocity = performance.now() - sweepStartedAt < 1500 ? motion.velocity : 0

    function paint() {
      if (needleElement.current) needleElement.current.style.transform = `rotate(${angle}deg)`
      motion = { angle, velocity }
    }
    function tick(now) {
      frame = null
      const elapsed = now - sweepStartedAt
      const sweeping = elapsed < 1500
      const destination = sweeping ? (elapsed < 420 ? NEEDLE_PEAK : NEEDLE_REST) : target.current
      const delta = previousTime === null ? 1 / 60 : Math.min((now - previousTime) / 1000, 1 / 30)
      previousTime = now
      // A critically damped spring keeps position and velocity continuous when
      // another item is entered or a click reverses the sweep.
      const offset = angle - destination
      const damping = 15
      const impulse = velocity + damping * offset
      const decay = Math.exp(-damping * delta)
      angle = destination + (offset + impulse * delta) * decay
      velocity = (velocity - damping * impulse * delta) * decay
      const settled = Math.abs(angle - destination) < 0.01 && Math.abs(velocity) < 0.05
      if (settled) { angle = destination; velocity = 0 }
      paint()
      if (sweeping || !settled) frame = requestAnimationFrame(tick)
      else previousTime = null
    }
    function wake() {
      if (reducedMotion.matches) {
        if (frame !== null) cancelAnimationFrame(frame)
        frame = null
        previousTime = null
        angle = NEEDLE_REST
        velocity = 0
        paint()
      } else if (frame === null) {
        previousTime = null
        frame = requestAnimationFrame(tick)
      }
    }
    wakeMotion.current = wake
    sweepListeners.add(wake)
    reducedMotion.addEventListener('change', wake)
    wake()
    return () => {
      if (frame !== null) cancelAnimationFrame(frame)
      wakeMotion.current = null
      sweepListeners.delete(wake)
      reducedMotion.removeEventListener('change', wake)
    }
  }, [])

  return <Link className="brand travelly-brand" to="/" aria-label={t("Travelly home")}>
    <span className="brand-mark is-ready" aria-hidden="true">
      <img src={brandAssets + 'wordmark.png'} className="brand-wordmark-art" width="1579" height="428" alt="" fetchPriority="high" draggable="false"/>
      <span className="brand-speedometer">
        <img className="brand-speedometer-dial" src={dial} alt="" draggable="false"/>
        <img ref={needleElement} className="brand-gauge-needle" src={needle} alt="" draggable="false" style={{transform:`rotate(${initialAngle.current}deg)`}}/>
        <svg className="brand-gauge-hub" viewBox="435.5 649 250 250" focusable="false">
          <image href={needle} width="1536" height="1024"/>
        </svg>
      </span>
    </span>
  </Link>
}
