import test from 'node:test'
import assert from 'node:assert/strict'
import {speechLang,hasWord,answerOf,CONFIRM_SECONDS,hasVoice,speak,recognitionConstructor,readSetting,saveSetting,SPEAK_KEY} from '../src/features/driver/roadAlertSpeech.js'

const synth=voices=>({getVoices:()=>voices,spoken:[],speak(u){this.spoken.push(u)}})
class Utterance{constructor(text){this.text=text}}
test('speech language follows the selected language',()=>{
 assert.equal(speechLang('ta'),'ta-LK');assert.equal(speechLang('si'),'si-LK');assert.equal(speechLang('en'),'en-US');assert.equal(speechLang('xx'),'en-US')
})
const YES=['ஆம்','ஆமா','aam','yes','ok','ඔව්'],NO=['இல்லை','வேண்டாம்','no','එපා']
test('whole-word matching against the server word lists, in lower case',()=>{
 assert.equal(hasWord('Yes please',YES),true);assert.equal(hasWord('YES.',YES),true)
 assert.equal(hasWord('ஆம் அனுப்பு',YES),true);assert.equal(hasWord('ඔව් යවන්න',YES),true)
 // "ok" must not match inside another word; "no" not inside "know" or "yesno"
 assert.equal(hasWord('okay lets go',YES),false);assert.equal(hasWord('i know',NO),false);assert.equal(hasWord('yesterday',YES),false)
 assert.equal(hasWord('',YES),false);assert.equal(hasWord('yes',[]),false);assert.equal(hasWord('yes',undefined),false)
 // a phrase in the list matches whole words in a row
 assert.equal(hasWord('please send it now',['send it']),true);assert.equal(hasWord('resend it',['send it']),false)
})
test('answer: yes, no, both heard counts as no, anything else is no answer yet',()=>{
 assert.equal(answerOf('yes',YES,NO),'yes');assert.equal(answerOf('ஆம்',YES,NO),'yes');assert.equal(answerOf('ඔව් ඔව්',YES,NO),'yes')
 assert.equal(answerOf('no',YES,NO),'no');assert.equal(answerOf('வேண்டாம்',YES,NO),'no');assert.equal(answerOf('එපා',YES,NO),'no')
 assert.equal(answerOf('yes no',YES,NO),'no');assert.equal(answerOf('no yes',YES,NO),'no');assert.equal(answerOf('ஆம் இல்லை',YES,NO),'no')
 assert.equal(answerOf('what',YES,NO),null);assert.equal(answerOf('',YES,NO),null);assert.equal(answerOf('yes',[],[]),null)
})
test('the confirmation window defaults to 10 seconds when the server sends none',()=>{assert.equal(CONFIRM_SECONDS,10)})
test('a voice is used only when the device has one for the language',()=>{
 const s=synth([{lang:'en-GB'},{lang:'ta-IN'}])
 assert.equal(hasVoice('en-US',s),true);assert.equal(hasVoice('ta-LK',s),true);assert.equal(hasVoice('si-LK',s),false)
 assert.equal(speak('Hello','si-LK',{synth:s,Utterance}),false);assert.equal(s.spoken.length,0)
 assert.equal(speak('Hello','en-US',{synth:s,Utterance}),true);assert.equal(s.spoken[0].text,'Hello');assert.equal(s.spoken[0].lang,'en-US')
 assert.equal(speak('',"en-US",{synth:s,Utterance}),false)
 assert.equal(hasVoice('en-US',null),false)
})
test('browser speech recognition is optional',()=>{
 assert.equal(recognitionConstructor({}),null)
 const ctor=function(){};assert.equal(recognitionConstructor({webkitSpeechRecognition:ctor}),ctor)
})
test('the speaker choice is remembered on this device',()=>{
 const store=new Map(),storage={getItem:k=>store.get(k)??null,setItem:(k,v)=>store.set(k,v)}
 assert.equal(readSetting(storage),false);saveSetting(true,storage);assert.equal(store.get(SPEAK_KEY),'on');assert.equal(readSetting(storage),true)
 saveSetting(false,storage);assert.equal(readSetting(storage),false)
 assert.equal(readSetting({getItem(){throw new Error('blocked')}}),false)
})
