import {validateDocumentUpload} from './documentUpload.js'

export function applicationToday(now=new Date()){
 const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Colombo',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(now)
 const value=type=>parts.find(part=>part.type===type).value
 return `${value('year')}-${value('month')}-${value('day')}`
}
export function evidenceMetadataErrors(doc,today=applicationToday()){
 const errors={}
 if(doc.issue_date&&doc.issue_date>today)errors.issue_date='The issue date is in the future. Enter the date printed on the corrected document.'
 if(doc.expiry_date&&doc.expiry_date<today)errors.expiry_date='This document has expired. Upload current replacement evidence.'
 if(['PASSPORT','DRIVING_LICENCE'].includes(doc.document_type)&&!doc.expiry_date)errors.expiry_date='A current expiry date is required for role approval.'
 if(doc.document_type==='DRIVING_LICENCE'&&doc.issuing_country!=='LK')errors.issuing_country='Driver approval requires a Sri Lanka-issued driving licence.'
 return errors
}
export function reusableApplicationEvidence(doc,today=applicationToday()){
 return ['SUBMITTED','UNDER_REVIEW','APPROVED'].includes(doc.status)&&Object.keys(evidenceMetadataErrors(doc,today)).length===0
}
export function validateApplicationEvidence(body,today=applicationToday()){
 return {...evidenceMetadataErrors(Object.fromEntries(body),today),...validateDocumentUpload(body)}
}
