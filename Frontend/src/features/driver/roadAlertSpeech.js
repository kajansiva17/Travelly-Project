/* Speech helpers for road alerts (contract 03A). Recognition and speaking use the browser only; nothing is installed
   and nothing is sent anywhere except the recognised words, which go to POST /road-alerts/voice-classify. */
const LANG={en:'en-US',ta:'ta-LK',si:'si-LK'}
export const speechLang=code=>LANG[code]||LANG.en
export const SPEAK_KEY='travelly-speak-road-alerts'
export const CONFIRM_SECONDS=10   // used only if the server does not send confirm_seconds
// Words are lower case letters, marks and digits; everything else (spaces, punctuation) separates them.
const wordsOf=text=>String(text||'').toLowerCase().normalize('NFC').split(/[^\p{L}\p{N}\p{M}]+/u).filter(Boolean)
// Whole-word match (a phrase must match whole words in a row): "ok" never matches inside another word.
export function hasWord(text,list){
  const heard=' '+wordsOf(text).join(' ')+' '
  return (list||[]).some(entry=>{const phrase=wordsOf(entry).join(' ');return phrase&&heard.includes(' '+phrase+' ')})
}
// The Driver's spoken answer, from the server's yes_words and no_words. Both heard counts as no; neither is no answer yet.
export function answerOf(text,yesWords,noWords){
  const yes=hasWord(text,yesWords),no=hasWord(text,noWords)
  return no?'no':yes?'yes':null
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
// The clearest voice this device has for the language: the exact region first, then a network or "natural" voice.
export function pickVoice(lang,synth=globalThis.speechSynthesis){
  if(!synth||typeof synth.getVoices!=='function')return null
  const base=String(lang).slice(0,2).toLowerCase(),want=String(lang).toLowerCase().replace('_','-')
  const same=synth.getVoices().filter(voice=>String(voice.lang||'').slice(0,2).toLowerCase()===base)
  const score=voice=>(String(voice.lang||'').toLowerCase().replace('_','-')===want?4:0)+(/google|natural|neural|online/i.test(voice.name||'')?2:0)+(voice.localService===false?1:0)
  return same.length?[...same].sort((a,b)=>score(b)-score(a))[0]:null
}
// Says the text, slowly and clearly, when this device has a voice for the language. Returns true when it started speaking.
export function speak(text,lang,{onEnd,synth=globalThis.speechSynthesis,Utterance=globalThis.SpeechSynthesisUtterance}={}){
  if(!text||!synth||!Utterance||!hasVoice(lang,synth))return false
  try{synth.cancel&&synth.cancel()}catch{/* Nothing was speaking. */}
  const utterance=new Utterance(text)
  utterance.lang=lang
  utterance.rate=String(lang).slice(0,2).toLowerCase()==='en'?1:0.9   // Tamil and Sinhala are easier to follow a little slower
  utterance.pitch=1;utterance.volume=1
  const voice=pickVoice(lang,synth)
  if(voice)utterance.voice=voice
  if(onEnd){utterance.onend=onEnd;utterance.onerror=onEnd}
  synth.speak(utterance)
  return true
}
// Browsers load their voices late; asking once (and again when they arrive) makes the first alert speak too.
export function warmVoices(synth=globalThis.speechSynthesis){
  try{synth?.getVoices?.();synth?.addEventListener?.('voiceschanged',()=>synth.getVoices())}catch{/* No speech on this device. */}
}
// One alert, in the page language: the sentence written for that language, otherwise what the server worded for the person.
export const alertText=(item,language)=>item?.messages?.[language]||item?.message||''
export const alertName=(item,language)=>item?.names?.[language]||item?.name||''
