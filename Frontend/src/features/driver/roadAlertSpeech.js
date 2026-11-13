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
