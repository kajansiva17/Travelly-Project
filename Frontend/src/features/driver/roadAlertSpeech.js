/* Speech helpers for road alerts (contract 03A). Recognition and speaking use the browser only; nothing is installed
   and nothing is sent anywhere except the recognised words, which go to POST /road-alerts/voice-classify. */
const LANG={en:'en-US',ta:'ta-LK',si:'si-LK'}
export const speechLang=code=>LANG[code]||LANG.en
export const SPEAK_KEY='travelly-speak-road-alerts'
export const YES_WORDS=['yes','ஆம்','ඔව්']
const clean=text=>String(text||'').toLowerCase().normalize('NFC').replace(/[.,!?;:"'()]/g,' ').replace(/\s+/g,' ').trim()
// The spoken confirmation: "yes", "ஆம்" or "ඔව්" as a word of its own.
export function isYes(text){
  const words=clean(text).split(' ')
  return YES_WORDS.some(word=>words.includes(word))
}
export const recognitionConstructor=(scope=globalThis)=>scope.SpeechRecognition||scope.webkitSpeechRecognition||null
// A voice for this language is installed on this device (Tamil and Sinhala voices are not on every device).
export function hasVoice(lang,synth=globalThis.speechSynthesis){
  if(!synth||typeof synth.getVoices!=='function')return false
  const base=String(lang).slice(0,2).toLowerCase()
  return synth.getVoices().some(voice=>String(voice.lang||'').slice(0,2).toLowerCase()===base)
}
export function readSetting(storage=globalThis.localStorage){try{return storage?.getItem(SPEAK_KEY)==='on'}catch{return false}}
export function saveSetting(on,storage=globalThis.localStorage){try{storage?.setItem(SPEAK_KEY,on?'on':'off')}catch{/* The choice still works until the page closes. */}}
// Says the text when this device has a voice for the language. Returns true when it started speaking.
export function speak(text,lang,{onEnd,synth=globalThis.speechSynthesis,Utterance=globalThis.SpeechSynthesisUtterance}={}){
  if(!text||!synth||!Utterance||!hasVoice(lang,synth))return false
  const utterance=new Utterance(text)
  utterance.lang=lang
  const voice=synth.getVoices().find(v=>String(v.lang||'').slice(0,2).toLowerCase()===lang.slice(0,2).toLowerCase())
  if(voice)utterance.voice=voice
  if(onEnd){utterance.onend=onEnd;utterance.onerror=onEnd}
  synth.speak(utterance)
  return true
}
