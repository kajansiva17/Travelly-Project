import { t } from '../i18n/language.js'
import {ErrorNotice} from './components'

/* A vehicle or departure that can no longer be quoted, requested or held (409 VEHICLE_NOT_AVAILABLE / DEPARTURE_NOT_AVAILABLE,
   contract 03CM). The Passenger sees only the normal "not available" message and a way back to the search; never a reason. */
export const isNotAvailable=error=>error?.code==='VEHICLE_NOT_AVAILABLE'||error?.code==='DEPARTURE_NOT_AVAILABLE'
export default function NotAvailableNotice({error,action}){
  if(!error)return null
  if(!isNotAvailable(error))return <ErrorNotice error={error}/>
  return <div className="notice error cm-unavailable" role="alert"><span>{error.message||t('This is not available any more.')}</span> {action}</div>
}
