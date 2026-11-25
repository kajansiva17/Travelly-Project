import { t } from '../../i18n/language.js'
import { useEffect, useRef, useState } from 'react'

// Crop a picture to the 4:3 frame the vehicle cards show. The Owner drags the picture and zooms, so the vehicle is always inside the frame.
// onDone(dataUrl): a 640 x 480 JPEG (the server keeps at most 480 px on the long side); onCancel(): nothing is saved.
const OUT_W = 640, OUT_H = 480

export default function ImageCropper({ file, onDone, onCancel }) {
  const frame = useRef(null), drag = useRef(null)
  const [url, setUrl] = useState(''), [size, setSize] = useState(null), [zoom, setZoom] = useState(1), [pos, setPos] = useState({ x: 0, y: 0 }), [box, setBox] = useState({ w: 0, h: 0 }), [failed, setFailed] = useState(false)

  useEffect(() => { const u = URL.createObjectURL(file); setUrl(u); return () => URL.revokeObjectURL(u) }, [file])
  useEffect(() => { const key = event => { if (event.key === 'Escape') onCancel() }; window.addEventListener('keydown', key); return () => window.removeEventListener('keydown', key) }, [])

  const cover = size && box.w ? Math.max(box.w / size.w, box.h / size.h) : 1
  const scale = cover * zoom
  const clamp = (x, y, s = scale) => size ? { x: Math.min(0, Math.max(box.w - size.w * s, x)), y: Math.min(0, Math.max(box.h - size.h * s, y)) } : { x, y }

  function loaded(event) {
    const w = event.currentTarget.naturalWidth, h = event.currentTarget.naturalHeight, rect = frame.current.getBoundingClientRect()
    const s = Math.max(rect.width / w, rect.height / h)
    setSize({ w, h }); setBox({ w: rect.width, h: rect.height }); setPos({ x: (rect.width - w * s) / 2, y: (rect.height - h * s) / 2 })
  }
  function change(next) {
    const s = cover * next, cx = (box.w / 2 - pos.x) / scale, cy = (box.h / 2 - pos.y) / scale   // keep the middle of the frame where it is
    setZoom(next); setPos(clamp(box.w / 2 - cx * s, box.h / 2 - cy * s, s))
  }
  const down = event => { drag.current = { x: event.clientX, y: event.clientY, start: pos }; event.currentTarget.setPointerCapture?.(event.pointerId) }
  const move = event => { if (drag.current) setPos(clamp(drag.current.start.x + event.clientX - drag.current.x, drag.current.start.y + event.clientY - drag.current.y)) }
  const up = () => { drag.current = null }
  const keys = event => {
    const step = { ArrowLeft: [20, 0], ArrowRight: [-20, 0], ArrowUp: [0, 20], ArrowDown: [0, -20] }[event.key]
    if (step) { event.preventDefault(); setPos(clamp(pos.x + step[0], pos.y + step[1])) }
  }
  function done() {
    const image = frame.current.querySelector('img'), canvas = document.createElement('canvas')
    canvas.width = OUT_W; canvas.height = OUT_H
    const context = canvas.getContext('2d')
    context.fillStyle = '#fff'; context.fillRect(0, 0, OUT_W, OUT_H)
    context.drawImage(image, -pos.x / scale, -pos.y / scale, box.w / scale, box.h / scale, 0, 0, OUT_W, OUT_H)
    onDone(canvas.toDataURL('image/jpeg', 0.9))
  }

  return <div className="chat-backdrop" role="presentation">
    <section className="chat-panel crop-panel" role="dialog" aria-modal="true" aria-label={t('Adjust the picture')}>
      <header className="chat-head"><span className="chat-title">{t('Adjust the picture')}</span></header>
      <div className="crop-body">
        <p className="crop-help">{t('Drag the picture to move it. Use the slider to zoom. Passengers see exactly this frame.')}</p>
        <div ref={frame} className="crop-frame" tabIndex={0} onKeyDown={keys} onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}>
          {url && <img src={url} alt="" draggable={false} onLoad={loaded} onError={() => setFailed(true)}
            style={size ? { width: size.w * scale, height: size.h * scale, transform: `translate(${pos.x}px, ${pos.y}px)` } : { visibility: 'hidden' }}/>}
        </div>
        {failed && <p className="chat-problem" role="alert">{t('Unable to read this image.')}</p>}
        <label className="crop-zoom"><span>{t('Zoom')}</span><input type="range" min="1" max="4" step="0.02" value={zoom} onChange={event => change(Number(event.target.value))} disabled={!size}/></label>
      </div>
      <div className="chat-form crop-actions">
        <button type="button" className="ui-button ui-button-secondary" onClick={onCancel}>{t('Cancel')}</button>
        <button type="button" className="ui-button ui-button-primary" disabled={!size} onClick={done}>{t('Use this picture')}</button>
      </div>
    </section>
  </div>
}
