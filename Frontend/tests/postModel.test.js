import test from 'node:test'
import assert from 'node:assert/strict'
import {LIMITS,buildPostForm,checkDuration,checkVideoFile,problems,thumbSize,wholeSeconds} from '../src/features/social/postModel.js'

const file=(size,type='video/mp4')=>({size,type,name:'a.mp4'})
test('video size and type are checked before upload', () => {
  assert.equal(checkVideoFile(file(10)),'')
  assert.equal(checkVideoFile(file(LIMITS.reelBytes+1)),'TOO_LARGE')
  assert.equal(checkVideoFile(file(10,'video/x-flv')),'WRONG_TYPE')
  assert.equal(checkVideoFile(null),'MISSING')
})
test('length: over 60 seconds is refused, 60 is fine, unreadable is refused', () => {
  assert.equal(checkDuration(60),'');assert.equal(checkDuration(60.1),'TOO_LONG');assert.equal(checkDuration(NaN),'UNREADABLE');assert.equal(checkDuration(0),'UNREADABLE')
  assert.equal(wholeSeconds(0.2),1);assert.equal(wholeSeconds(41.2),42);assert.equal(wholeSeconds(60),60)
})
test('thumbnail keeps the shape and at most 720 on the long side', () => {
  assert.deepEqual(thumbSize(1080,1920),{width:405,height:720});assert.deepEqual(thumbSize(300,200),{width:300,height:200});assert.deepEqual(thumbSize(0,0),{width:0,height:0})
})
test('what blocks the Post button', () => {
  assert.deepEqual(problems({post_type:'REEL',visibility:'PUBLIC',file:file(10),duration:30}),[])
  assert.ok(problems({post_type:'REEL',visibility:'PUBLIC',file:file(10),duration:61}).includes('file'))
  assert.deepEqual(problems({post_type:'REVIEW',visibility:'PUBLIC',caption:'',rating:0,linked_vehicle_id:''}).sort(),['caption','linked_vehicle_id','rating'])
  assert.ok(problems({post_type:'PHOTO',visibility:'PUBLIC',file:null}).includes('file'))
  assert.ok(problems({post_type:'PHOTO',visibility:'PUBLIC',file:file(1,'image/jpeg'),hashtags:Array.from({length:31},(_,i)=>'t'+i).join(',')}).includes('hashtags'))
})
test('multipart body: fields per post type, empty optionals left out', () => {
  const reel=buildPostForm({post_type:'REEL',visibility:'FOLLOWERS',file:new Blob(['x']),thumbnail:new Blob(['y']),duration:41.2,caption:' Ella #ella ',hashtags:'ella, train',location_name:''})
  assert.equal(reel.get('post_type'),'REEL');assert.equal(reel.get('visibility'),'FOLLOWERS');assert.equal(reel.get('duration_seconds'),'42')
  assert.ok(reel.get('file'));assert.ok(reel.get('thumbnail'));assert.equal(reel.get('caption'),'Ella #ella');assert.equal(reel.get('hashtags'),'["ella","train"]');assert.equal(reel.has('location_name'),false);assert.equal(reel.has('rating'),false)
  const review=buildPostForm({post_type:'REVIEW',visibility:'PUBLIC',caption:'Good',linked_vehicle_id:'v1',rating:5})
  assert.equal(review.get('linked_vehicle_id'),'v1');assert.equal(review.get('rating'),'5');assert.equal(review.has('file'),false);assert.equal(review.has('duration_seconds'),false)
})
