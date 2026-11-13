import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createAiRequests} from '../src/features/ai/aiClient.js'
import {helpTarget} from '../src/features/ai/aiHelp.js'
import {aiErrorText} from '../src/features/ai/aiApi.js'

// Signed-in only (contract 03AI): every AI call goes through the normal API client, which sends the Bearer token.
test('all three AI calls go through the injected API client with the documented paths and bodies',async()=>{
 const calls=[],client=async(path,options={})=>{calls.push({path,options});return {ok:true}}
 const ai=createAiRequests(client)
 await ai.searchAssist({message:'Kandy to Colombo',language:'ta',filters:{pickup:'Kandy'},asking:'service'})
 await ai.searchAssist({message:'hello',language:'en'})
 await ai.askHelp({question:'how to cancel',language:'si'})
 await ai.helpTopics('ta')
 assert.deepEqual(calls.map(c=>c.path),['/ai/search-assist','/ai/search-assist','/ai/help','/ai/help/topics/ta'])
 assert.deepEqual(calls.map(c=>c.options.method),['POST','POST','POST',undefined])
 assert.deepEqual(JSON.parse(calls[0].options.body),{message:'Kandy to Colombo',language:'ta',filters:{pickup:'Kandy'},asking:'service'})
 assert.deepEqual(JSON.parse(calls[1].options.body),{message:'hello',language:'en',filters:{},asking:null})   // the first turn starts with filters {} and asking null
 assert.deepEqual(JSON.parse(calls[2].options.body),{question:'how to cancel',language:'si'})
})
test('the AI requests use the app API client and never the public (no sign-in) helpers',()=>{
 const source=readFileSync(new URL('../src/features/ai/aiRequests.js',import.meta.url),'utf8')
 assert.match(source,/import \{api\} from '..\/..\/services\/api'/)
 assert.doesNotMatch(source,/publicRead|publicRequest|publicAuth/)
})
test('errors become friendly lines: ended session, wrong length, rate limit, network, anything else',()=>{
 assert.equal(aiErrorText(Object.assign(new Error('Please sign in again.'),{status:401})),'Please sign in again to use Travelly AI.')
 assert.equal(aiErrorText(Object.assign(new Error('x'),{status:422,code:'VALIDATION_ERROR'})),'Your message must be between 1 and 500 characters.')
 assert.match(aiErrorText(Object.assign(new Error('raw'),{status:429,code:'RATE_LIMITED'})),/Too many questions/)
 assert.equal(aiErrorText(new TypeError('Failed to fetch')),'We could not reach Travelly. Please try again.')
 for(const status of [400,403,500,503])assert.equal(aiErrorText(Object.assign(new Error('Traceback boom'),{status})),'Travelly AI could not answer just now. Please try again.')
})

// Help paths are Passenger paths (clarification 1): the button opens the person's own workspace copy.
test('help paths map to the workspace: support, travel and bookings, dashboard',()=>{
 const owner={role:'OWNER',allowed:['PASSENGER','OWNER']},driver={role:'DRIVER',allowed:['PASSENGER','DRIVER']},passenger={role:'PASSENGER',allowed:['PASSENGER']}
 assert.equal(helpTarget('/passenger/support',passenger),'/passenger/support')
 assert.equal(helpTarget('/passenger/support',owner),'/owner/support')
 assert.equal(helpTarget('/passenger/support',driver),'/driver/support')
 assert.equal(helpTarget('/bookings',owner),'/owner/travel/bookings');assert.equal(helpTarget('/bookings',driver),'/driver/travel/bookings');assert.equal(helpTarget('/bookings',passenger),'/bookings')
 assert.equal(helpTarget('/travel/book/tickets',owner),'/owner/travel/book/tickets')
 assert.equal(helpTarget('/dashboard',owner),'/owner/dashboard');assert.equal(helpTarget('/dashboard',driver),'/driver/dashboard');assert.equal(helpTarget('/dashboard',passenger),'/dashboard')
})
test('Owner and Driver topics show the button only to people with that approved role',()=>{
 const owner={role:'OWNER',allowed:['PASSENGER','OWNER']},passenger={role:'PASSENGER',allowed:['PASSENGER']},both={role:'OWNER',allowed:['PASSENGER','OWNER','DRIVER']}
 assert.equal(helpTarget('/owner/vehicles',owner),'/owner/vehicles');assert.equal(helpTarget('/owner/vehicles',passenger),null)
 assert.equal(helpTarget('/driver/assignments',owner),null);assert.equal(helpTarget('/driver/assignments',both),'/driver/assignments')
 assert.equal(helpTarget('/owner/earnings',{role:'DRIVER',allowed:['PASSENGER','DRIVER']}),null)
})
test('account, forgot-password, reels and the onboarding pages are used as given; nothing is opened without a path',()=>{
 const passenger={role:'PASSENGER',allowed:['PASSENGER']},owner={role:'OWNER',allowed:['PASSENGER','OWNER']}
 for(const path of ['/account','/forgot-password','/reels','/owner/onboarding','/driver/onboarding'])for(const who of [passenger,owner])assert.equal(helpTarget(path,who),path)
 assert.equal(helpTarget(null,owner),null);assert.equal(helpTarget('',owner),null);assert.equal(helpTarget('https://example.com',owner),null)
})
