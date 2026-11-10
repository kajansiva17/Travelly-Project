import { t } from '../i18n/language.js'
import React, { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'

const brandAssets = '/images/travelly/branding/approved-2026-11-07/'
const dial = brandAssets + 'meter-dial.png'
const needle = brandAssets + 'meter-needle.png'
export const NEEDLE_REST = -132
export const NEEDLE_PEAK = 18

// One shared speedometer needle for every navbar (app, landing, sign-in). The needle is its own <img> and only ever
// changes its CSS rotate(). Mouse x across the navbar sets a target angle; a click on any control sweeps to full and back.
// Motion survives navigation (the header remounts), so the needle never jumps.
const SWEEP_MS = 800
let sweepStartedAt = -Infinity
let sweepFrom = NEEDLE_REST
let target = NEEDLE_REST
let motion = { angle: NEEDLE_REST, velocity: 0 }
const listeners = new Set()
const wakeAll = () => listeners.forEach(wake => wake())
const ease = q => (1 - Math.cos(Math.PI * Math.min(1, Math.max(0, q)))) / 2

export function setNeedleTarget(angle) { target = angle; wakeAll() }
export function sweepNavbarNeedle() { sweepFrom = motion.angle; sweepStartedAt = performance.now(); wakeAll() }

// Attach to the navbar element: x position -> angle, leave -> rest, click on a control -> sweep.
export function useNeedleEvents(ref) {
  useEffect(() => {
    const element = ref.current
    if (!element) return undefined
    const move = event => {
      if (event.pointerType && event.pointerType !== 'mouse') return
      const box = element.getBoundingClientRect()
      const fraction = box.width ? Math.min(1, Math.max(0, (event.clientX - box.left) / box.width)) : 0
      setNeedleTarget(NEEDLE_REST + fraction * (NEEDLE_PEAK - NEEDLE_REST))
    }
    const leave = () => setNeedleTarget(NEEDLE_REST)
    const click = event => { if (event.target instanceof Element && event.target.closest('a, button, summary, select')) { setNeedleTarget(NEEDLE_REST); sweepNavbarNeedle() } }
    element.addEventListener('pointermove', move)
    element.addEventListener('pointerleave', leave)
    element.addEventListener('click', click, true)
    return () => { element.removeEventListener('pointermove', move); element.removeEventListener('pointerleave', leave); element.removeEventListener('click', click, true); setNeedleTarget(NEEDLE_REST) }
  }, [ref])
}

export default function TravellyBrand() {
  const needleElement = useRef(null)
  const initialAngle = useRef(null)
  if (initialAngle.current === null) {
    initialAngle.current = performance.now() - sweepStartedAt < SWEEP_MS ? motion.angle : target
  }

  useEffect(() => {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
    let frame = null
    let previousTime = null
    let angle = initialAngle.current
    let velocity = performance.now() - sweepStartedAt < SWEEP_MS ? motion.velocity : 0

    function paint() {
      if (needleElement.current) needleElement.current.style.transform = `rotate(${angle}deg)`
      motion = { angle, velocity }
    }
    function tick(now) {
      frame = null
      const elapsed = now - sweepStartedAt
      const sweeping = elapsed < SWEEP_MS
      const delta = previousTime === null ? 1 / 60 : Math.min((now - previousTime) / 1000, 1 / 30)
      previousTime = now
      if (sweeping) {
        // up to full and back, ease-in-out on both halves; continuous with the angle it started from and the hover target
        const p = elapsed / SWEEP_MS
        angle = p < .5 ? sweepFrom + (NEEDLE_PEAK - sweepFrom) * ease(p * 2) : NEEDLE_PEAK + (target - NEEDLE_PEAK) * ease((p - .5) * 2)
        velocity = 0
      } else {
        // critically damped spring: smooth, no overshoot, keeps position and velocity continuous
        const offset = angle - target
        const damping = 15
        const impulse = velocity + damping * offset
        const decay = Math.exp(-damping * delta)
        angle = target + (offset + impulse * delta) * decay
        velocity = (velocity - damping * impulse * delta) * decay
        if (Math.abs(angle - target) < 0.01 && Math.abs(velocity) < 0.05) { angle = target; velocity = 0 }
      }
      paint()
      const settled = !sweeping && angle === target && velocity === 0
      if (!settled) frame = requestAnimationFrame(tick)
      else previousTime = null
    }
    function wakeMotion() {
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
    listeners.add(wakeMotion)
    reducedMotion.addEventListener('change', wakeMotion)
    wakeMotion()
    return () => {
      if (frame !== null) cancelAnimationFrame(frame)
      listeners.delete(wakeMotion)
      reducedMotion.removeEventListener('change', wakeMotion)
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
