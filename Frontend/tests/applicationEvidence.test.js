import test from 'node:test'
import assert from 'node:assert/strict'
import {applicationToday,evidenceMetadataErrors,reusableApplicationEvidence,validateApplicationEvidence} from '../src/services/applicationEvidence.js'
const today='2026-11-06'
function body(type,values={}){const result=new FormData();result.set('document_type',type);result.set('file',new File(['evidence'],'evidence.png',{type:'image/png'}));for(const [key,value] of Object.entries(values))result.set(key,value);return result}
test('role applications require replacement of future, expired, rejected and correction evidence',()=>{
 for(const status of ['SUBMITTED','UNDER_REVIEW','APPROVED'])assert.equal(reusableApplicationEvidence({document_type:'NIC',status,issue_date:'2026-11-07'},today),false)
 for(const status of ['REJECTED','NEEDS_CORRECTION'])assert.equal(reusableApplicationEvidence({document_type:'NIC',status},today),false)
 assert.equal(reusableApplicationEvidence({document_type:'NIC',status:'APPROVED'},today),true)
 assert.equal(reusableApplicationEvidence({document_type:'NIC',status:'APPROVED',expiry_date:'2026-11-05'},today),false)
})
test('Passport and Driver evidence retain the existing required-expiry and Sri Lanka checks',()=>{
 assert.ok(evidenceMetadataErrors({document_type:'PASSPORT'},today).expiry_date)
 assert.ok(evidenceMetadataErrors({document_type:'DRIVING_LICENCE',issuing_country:'GB',expiry_date:'2030-01-01'},today).issuing_country)
 assert.deepEqual(evidenceMetadataErrors({document_type:'DRIVING_LICENCE',issuing_country:'LK',expiry_date:today},today),{})
})
test('new role evidence validates dates before upload without relaxing file checks',()=>{
 assert.ok(validateApplicationEvidence(body('NIC',{issue_date:'2026-11-07'}),today).issue_date)
 assert.ok(validateApplicationEvidence(body('PASSPORT'),today).expiry_date)
 assert.ok(validateApplicationEvidence(body('NIC',{issue_date:'2026-02-30'}),today).issue_date)
 assert.deepEqual(validateApplicationEvidence(body('NIC',{issue_date:today}),today),{})
})
test('role evidence uses the same Sri Lanka date boundary as server approval',()=>{
 assert.equal(applicationToday(new Date('2026-11-05T19:00:00Z')),today)
 assert.equal(applicationToday(new Date('2026-11-05T18:00:00Z')),'2026-11-05')
})
