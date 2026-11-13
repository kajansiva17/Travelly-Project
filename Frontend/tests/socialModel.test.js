import test from 'node:test'
import assert from 'node:assert/strict'
import {feedQuery,parseTags,ratingOf,replaceItem,sharePath,visibleInTab,withFollow} from '../src/features/social/socialModel.js'

test('feed query per tab, hashtag and page', () => {
  assert.equal(feedQuery({tab:'REEL',limit:8}),'type=REEL&limit=8')
  assert.equal(feedQuery({tab:'PHOTO',hashtag:'#ella',before:'abc'}),'type=PHOTO&hashtag=ella&before=abc&limit=20')
  assert.equal(feedQuery({tab:'FOLLOWING'}),'limit=20')
})
test('Following keeps only followed authors', () => {
  assert.equal(visibleInTab('FOLLOWING',{following_author:false}),false)
  assert.equal(visibleInTab('FOLLOWING',{following_author:true}),true)
  assert.equal(visibleInTab('REEL',{following_author:false}),true)
})
test('follow, replace, rating, tags and share link helpers', () => {
  const items=[{id:'1',author:{reference:'A'},following_author:false},{id:'2',author:{reference:'B'},following_author:false}]
  assert.deepEqual(withFollow(items,'A',true).map(i=>i.following_author),[true,false])
  assert.equal(replaceItem(items,{id:'2',like_count:3})[1].like_count,3)
  assert.equal(ratingOf({rating:4.4}),4);assert.equal(ratingOf({rating:null}),0);assert.equal(ratingOf({rating:9}),5)
  assert.deepEqual(parseTags('ella, #beach  ella'),['ella','beach'])
  assert.equal(sharePath('https://x.lk/','/reels/1'),'https://x.lk/reels/1')
})
