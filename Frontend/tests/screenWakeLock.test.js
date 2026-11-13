import test from 'node:test'
import assert from 'node:assert/strict'
import {wakeLockSupported,acquireWakeLock,releaseWakeLock} from '../src/features/driver/screenWakeLock.js'

const lock=()=>({released:false,async release(){this.released=true}})
test('wake lock supported: asks for the screen lock and returns it',async()=>{
 const held=lock(),calls=[],nav={wakeLock:{request:async type=>{calls.push(type);return held}}}
 assert.equal(wakeLockSupported(nav),true)
 const result=await acquireWakeLock(nav)
 assert.deepEqual(calls,['screen']);assert.equal(result.status,'held');assert.equal(result.lock,held)
 await releaseWakeLock(held);assert.equal(held.released,true)
 await releaseWakeLock(held);await releaseWakeLock(null)   // releasing twice or nothing never throws
})
test('wake lock unsupported: no error, just a status the page turns into a tip',async()=>{
 for(const nav of [{},{wakeLock:{}},null,undefined]){
  assert.equal(wakeLockSupported(nav),false)
  const result=await acquireWakeLock(nav);assert.equal(result.status,'unsupported');assert.equal(result.lock,null)
 }
})
test('wake lock refused by the browser: failed, never thrown',async()=>{
 const nav={wakeLock:{request:async()=>{throw new DOMException('Not allowed','NotAllowedError')}}}
 const result=await acquireWakeLock(nav);assert.equal(result.status,'failed');assert.equal(result.lock,null)
})
