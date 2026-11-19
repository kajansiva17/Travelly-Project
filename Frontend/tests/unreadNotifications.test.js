import test from 'node:test'
import assert from 'node:assert/strict'
import {NOTIFICATION_POLL_MS,unreadBadge} from '../src/features/notifications/unread.js'

test('notification badge hides zero, shows unread totals and caps large counts',()=>{
  assert.equal(unreadBadge(0),'')
  assert.equal(unreadBadge(null),'')
  assert.equal(unreadBadge(7),'7')
  assert.equal(unreadBadge(99),'99')
  assert.equal(unreadBadge(100),'99+')
  assert.equal(NOTIFICATION_POLL_MS,15_000)
})
