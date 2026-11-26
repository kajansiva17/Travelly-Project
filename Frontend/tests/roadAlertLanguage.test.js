import test from 'node:test'
import assert from 'node:assert/strict'
import {alertText,alertName,pickVoice} from '../src/features/driver/roadAlertSpeech.js'

const item={message:'Police ahead.',name:'Police',messages:{en:'Police ahead.',ta:'முன்னால் போலீஸ்.',si:'ඉදිරියෙන් පොලිසිය.'},names:{en:'Police',ta:'போலீஸ்',si:'පොලිසිය'}}
test('an alert is read in the language of the page, not the language of the Driver who reported it',()=>{
 assert.equal(alertText(item,'ta'),'முன்னால் போலீஸ்.');assert.equal(alertText(item,'si'),'ඉදිරියෙන් පොලිසිය.');assert.equal(alertText(item,'en'),'Police ahead.')
 assert.equal(alertName(item,'ta'),'போலீஸ்')
 // an older answer without the language map still reads
 assert.equal(alertText({message:'Police ahead.'},'ta'),'Police ahead.');assert.equal(alertName({name:'Police'},'si'),'Police');assert.equal(alertText(null,'en'),'')
})
test('the clearest voice is chosen: exact region first, then a network or natural voice',()=>{
 const synth={getVoices:()=>[{lang:'ta-IN',name:'Plain',localService:true},{lang:'ta-LK',name:'Plain LK',localService:true},{lang:'ta-IN',name:'Google தமிழ்',localService:false},{lang:'en-US',name:'x'}]}
 assert.equal(pickVoice('ta-LK',synth).name,'Plain LK')
 assert.equal(pickVoice('ta-IN',synth).name,'Google தமிழ்')
 assert.equal(pickVoice('si-LK',synth),null);assert.equal(pickVoice('ta-LK',null),null)
 assert.equal(pickVoice('en-US',synth).name,'x')
})
