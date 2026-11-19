p = 'src/styles/authGlass.css'
s = open(p, encoding='utf8').read()
# A: layout + vehicle card
a = s.index('/* Both cards share one row')
b = s.index('/* ---- Right: frosted form card ---- */')
A = '''/* ONE set of card tokens for Login, Register (every step), Forgot password, the code screen and Google completion: the form card has the same
   width, height and top offset everywhere. The vehicle card is a fixed share of it and is centred beside it. */
html body .auth-page {
  --auth-card-w: min(480px, calc(100vw - 40px));
  --auth-gap-y: clamp(10px, 2.4vh, 28px);
  --auth-card-h: min(640px, calc(100dvh - var(--frame-top) - var(--nav-h) - 2 * var(--auth-gap-y)));
  --auth-card-top: max(var(--auth-gap-y), calc((100dvh - var(--frame-top) - var(--nav-h) - var(--auth-card-h)) / 2));
  --auth-vcard-ratio: .88;
  --auth-vcard-w: calc(var(--auth-card-w) * var(--auth-vcard-ratio));
  --auth-vcard-h: calc(var(--auth-card-h) * var(--auth-vcard-ratio));
  --auth-pad-x: clamp(22px, 3vw, 40px); --auth-pad-y: clamp(14px, 2.6vh, 30px);
  --auth-gap: 12px;
}
html body .auth-page .auth-layout {
  flex: 1 1 auto; min-height: 0; width: 100%; margin: 0 auto; box-sizing: border-box;
  display: grid; grid-template-columns: var(--auth-vcard-w) var(--auth-card-w); grid-template-rows: var(--auth-card-h); justify-content: center; align-content: start; align-items: center;
  column-gap: clamp(24px, 3.4vw, 56px); padding: var(--auth-card-top) 20px 0;
}

/* ---- Left: ticket card (smaller than the form card, vertically centred against it) ---- */
html body .auth-page .auth-brand-panel { display: flex; align-items: center; min-width: 0; padding: 0; background: none; }
html body .auth-page .journey-pass-frame { display: flex; width: 100%; height: var(--auth-vcard-h); filter: drop-shadow(0 16px 30px rgb(18 40 90 / .3)) drop-shadow(0 0 7px rgb(255 226 150 / .22)); }
html body .auth-page .journey-pass {
  position: relative; flex: 1 1 auto; display: grid; justify-items: center; align-content: space-evenly; gap: clamp(6px, 1.4vh, 14px); padding: clamp(12px, 2vh, 24px) clamp(16px, 1.8vw, 24px);
  border-radius: 28px; box-sizing: border-box; min-height: 0; overflow: hidden;
  background: linear-gradient(180deg, rgb(255 255 255 / .5), rgb(255 255 255 / .3));
  -webkit-backdrop-filter: blur(16px) saturate(1.2); backdrop-filter: blur(16px) saturate(1.2);
  box-shadow: inset 0 0 0 1.5px rgb(255 255 255 / .7);
  -webkit-mask: radial-gradient(circle 9px at 0 50%, #0000 98%, #000) left / 51% 38px repeat-y, radial-gradient(circle 9px at 100% 50%, #0000 98%, #000) right / 51% 38px repeat-y;
  mask: radial-gradient(circle 9px at 0 50%, #0000 98%, #000) left / 51% 38px repeat-y, radial-gradient(circle 9px at 100% 50%, #0000 98%, #000) right / 51% 38px repeat-y;
}
html body .auth-page .journey-pass h2 { margin: 0; text-align: center; font-size: clamp(16px, 2.6vh, 24px); line-height: 1.25; font-weight: 800; letter-spacing: .01em; text-transform: uppercase; color: var(--ui-ink); overflow-wrap: break-word; }
html body .auth-page .journey-pass h2 span { color: var(--ag-red); }
html body .auth-page .journey-rule { display: block; width: 25%; height: 3px; border-radius: 2px; background: var(--ag-red); }
/* the four vehicles stand on one ground line (their tyre bottoms), evenly spaced, none overlapping, each with a soft ground shadow */
html body .auth-page .journey-fleet { position: relative; display: flex; align-items: flex-end; justify-content: space-evenly; width: 100%; padding-bottom: 8px; box-sizing: border-box; }
html body .auth-page .journey-fleet::after { content: ''; position: absolute; left: 4%; right: 4%; bottom: 3px; height: 2px; border-radius: 2px; background: linear-gradient(90deg, rgb(18 21 82 / 0), rgb(18 21 82 / .22) 14%, rgb(18 21 82 / .22) 86%, rgb(18 21 82 / 0)); }
html body .auth-page .journey-vehicle { position: relative; flex: none; display: block; aspect-ratio: var(--v-w) / var(--v-h); }
html body .auth-page .journey-vehicle::before { content: ''; position: absolute; left: 3%; right: 3%; bottom: -4px; height: 9px; border-radius: 50%; background: radial-gradient(ellipse at center, rgb(18 21 82 / .4), rgb(18 21 82 / 0) 72%); }
html body .auth-page .journey-vehicle img { position: absolute; z-index: 1; display: block; max-width: none; width: var(--v-scale); height: auto; left: var(--v-left); top: var(--v-top); }
html body .auth-page .journey-vehicle-bus { width: 28%; } html body .auth-page .journey-vehicle-van { width: 24%; }
html body .auth-page .journey-vehicle-car { width: 22%; } html body .auth-page .journey-vehicle-tuk-tuk { width: 15%; }
html body .auth-page .journey-services { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); width: 100%; margin: 0; padding: 0; list-style: none; }
html body .auth-page .journey-services li { display: grid; justify-items: center; align-content: start; gap: 8px; padding: 0 8px; text-align: center; font-size: clamp(12px, 1.8vh, 15px); line-height: 1.25; font-weight: 800; color: var(--ui-ink); }
html body .auth-page .journey-services li + li { border-left: 1px solid rgb(18 21 82 / .2); }
html body .auth-page .journey-services svg { color: var(--ag-red); }
html body .auth-page .journey-services span { overflow-wrap: break-word; }
html body .auth-page .journey-steps { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) auto minmax(0, 1fr); align-items: start; gap: 8px; width: 100%; margin: 0; padding: 10px 12px; box-sizing: border-box; list-style: none; border-radius: 18px; background: rgb(255 255 255 / .42); border: 1px solid rgb(255 255 255 / .7); }
html body .auth-page .journey-steps li:not(.journey-arrow) { display: grid; justify-items: center; align-content: start; gap: 6px; min-width: 0; text-align: center; }
html body .auth-page .journey-steps b { flex: none; display: grid; place-items: center; width: 30px; height: 30px; border-radius: 50%; color: #fff; font-size: 13px; font-weight: 800; background: var(--ui-red-gradient); box-shadow: 0 2px 6px rgb(var(--brand-red-rgb) / .35); }
html body .auth-page .journey-steps span { display: block; font-size: 12px; line-height: 1.25; font-weight: 600; color: var(--ui-ink); overflow-wrap: break-word; }
html body .auth-page .journey-arrow { align-self: start; margin-top: 7px; color: var(--ui-ink); }

'''
s = s[:a] + A + s[b:]
# B: form card
a = s.index('/* ---- Right: frosted form card ---- */')
b = s.index('html body .auth-page .auth-heading {')
B = '''/* ---- Right: frosted form card (fixed size; a step with more content scrolls inside it, the page never scrolls) ---- */
html body .auth-page .auth-form-panel {
  display: flex; flex-direction: column; justify-self: center; align-self: center; width: var(--auth-card-w); height: var(--auth-card-h); box-sizing: border-box; min-width: 0;
  padding: var(--auth-pad-y) var(--auth-pad-x); border-radius: 34px; overflow-x: hidden; overflow-y: auto; overscroll-behavior: contain; scrollbar-width: thin; scrollbar-color: rgb(18 21 82 / .3) transparent;
  background: linear-gradient(180deg, rgb(255 255 255 / .62), rgb(255 255 255 / .42));
  -webkit-backdrop-filter: blur(18px) saturate(1.25); backdrop-filter: blur(18px) saturate(1.25);
  border: 1.5px solid rgb(255 255 255 / .85); box-shadow: 0 18px 40px rgb(18 40 90 / .28), inset 0 1px 0 rgb(255 255 255 / .9);
}
html body .auth-page .auth-form-inner { display: grid; gap: var(--auth-gap); width: 100%; max-width: none; margin-block: auto; }
'''
s = s[:a] + B + s[b:]
# C: drop the old tail (sunlight, media blocks, Tamil wrap block); a new tail follows
a = s.index("/* Sunlight travelling around the journey card's border")
s = s[:a]
open(p, 'w', encoding='utf8').write(s)
print('ok', len(s))
