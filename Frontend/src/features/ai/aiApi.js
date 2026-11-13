import {t} from '../../i18n/language.js'

/* Travelly AI (contract 03AI). Every endpoint is public, so these calls carry no sign-in and work signed in or out.
   Nothing is stored, held or booked by the AI. */
// The topics list as plain {title, path?} rows; accepts {items:[...]} or a bare list.
export const topicRows=result=>(Array.isArray(result)?result:result?.items||result?.topics||[]).map(row=>({id:row.topic_id||row.id||row.title,title:row.title||row.question||String(row.topic_id||''),path:row.path||null})).filter(row=>row.title)

// A person never sees a raw error: network, time-out, rate limit (429 RATE_LIMITED) and anything else each get one friendly line.
export function aiErrorText(error){
  if(error instanceof TypeError||error?.code==='API_TIMEOUT')return t('We could not reach Travelly. Please try again.')
  if(error?.status===429||error?.code==='RATE_LIMITED')return t('Too many questions in a short time. Please wait a few minutes and try again.')
  return t('Travelly AI could not answer just now. Please try again.')
}
