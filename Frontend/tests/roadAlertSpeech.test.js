import test from 'node:test'
import assert from 'node:assert/strict'
import {speechLang,isYes,hasVoice,speak,recognitionConstructor,readSetting,saveSetting,SPEAK_KEY} from '../src/features/driver/roadAlertSpeech.js'

const synth=voices=>({getVoices:()=>voices,spoken:[],speak(u){this.spoken.push(u)}})
class Utterance{constructor(text){this.text=text}}
test('speech language follows the selected language',()=>{
 assert.equal(speechLang('ta'),'ta-LK');assert.equal(speechLang('si'),'si-LK');assert.equal(speechLang('en'),'en-US');assert.equal(speechLang('xx'),'en-US')
})
test('spoken yes words: yes, ஆம் and ඔව් confirm; anything else does not',()=>{
 for(const said of ['yes','Yes.','yes please','ஆம்','ஆம் அனுப்பு','ඔව්','ඔව් යවන්න'])assert.equal(isYes(said),true,said)
 for(const said of ['no','yesterday','','நிறுத்து','ඔබ'])assert.equal(isYes(said),false,said)
})
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
