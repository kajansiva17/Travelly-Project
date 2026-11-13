import {t} from '../../i18n/language.js'

// The topics list as plain {title, path?} rows; accepts {items:[...]} or a bare list.
export const topicRows=result=>(Array.isArray(result)?result:result?.items||result?.topics||[]).map(row=>({id:row.topic_id||row.id||row.title,title:row.title||row.question||String(row.topic_id||''),path:row.path||null})).filter(row=>row.title)

// A person never sees a raw error: a network failure or time-out, an ended session (401), a message of the wrong length (422),
// the rate limit (429 RATE_LIMITED) and anything else each get one friendly line.
export function aiErrorText(error){
  if(error instanceof TypeError||error?.code==='API_TIMEOUT')return t('We could not reach Travelly. Please try again.')
  if(error?.status===401)return t('Please sign in again to use Travelly AI.')
  if(error?.status===429||error?.code==='RATE_LIMITED')return t('Too many questions in a short time. Please wait a few minutes and try again.')
  if(error?.status===422||error?.code==='VALIDATION_ERROR')return t('Your message must be between 1 and 500 characters.')
  return t('Travelly AI could not answer just now. Please try again.')
}
