import {useState} from 'react'
import {api} from '../../services/api'
import {t} from '../../i18n/language.js'
import {Field,RateErrors} from '../owner/OwnerRates'
import {fieldErrorText} from '../../services/fieldErrors.js'
import {checkAirports,checkMinKm} from './serviceRulesModel.js'

// Long distance: the minimum road distance of a trip (default 100 km, 0 = no minimum). PATCH /admin/service-types/{id}/distance-rule.
export function DistanceRuleForm({row,onSaved}){
  const [km,setKm]=useState(String(row.min_distance_km??100)),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[errors,setErrors]=useState({})
  async function save(event){
    event.preventDefault();setMessage('');setErrors({})
    const problem=checkMinKm(km)
    if(problem){setErrors({min_distance_km:t(problem)});return}
    setBusy(true)
    try{await api(`/admin/service-types/${row.id}/distance-rule`,{method:'PATCH',body:JSON.stringify({expected_version:row.version,min_distance_km:Number(km)})});setMessage(t('Saved.'));onSaved()}
    catch(error){if(error.code==='VERSION_CONFLICT'){setMessage(t('This service was changed. The page was reloaded; check the value and save again.'));onSaved()}else setMessage(fieldErrorText(error,t('The distance could not be saved. Please try again.')))}
    finally{setBusy(false)}
  }
  return <RateErrors.Provider value={errors}><form className="flow-wizard-form tk-pane" onSubmit={save} noValidate>
    <div className="tk-grid" style={{'--cols':2}}>
      <Field label="Minimum trip distance (km)" help="A trip shorter than this cannot be booked as Long distance; the Passenger is asked to choose Local hire. The road distance of the whole trip counts, all days together. 0 means no minimum."><input required name="min_distance_km" type="number" min="0" max="2000" step="1" inputMode="numeric" value={km} onChange={event=>setKm(event.target.value)}/></Field>
      <div className="flow-actions"><span/><button type="submit" className="ui-button ui-button-primary" disabled={busy}>{busy?t('Saving…'):t('Save distance rule')}</button></div>
    </div>
    {message&&<p className="tk-line" role="status">{message}</p>}
  </form></RateErrors.Provider>
}

// Airport hire: the list Passengers choose from. PUT /admin/service-types/{id}/airports replaces the whole list.
export function AirportListForm({row,onSaved}){
  const [list,setList]=useState(()=>(row.airports||[]).map(item=>({...item}))),[busy,setBusy]=useState(false),[message,setMessage]=useState('')
  const change=(index,name,value)=>setList(rows=>rows.map((item,i)=>i===index?{...item,[name]:value}:item))
  async function save(event){
    event.preventDefault();setMessage('')
    const problem=checkAirports(list)
    if(problem){setMessage(t(problem));return}
    setBusy(true)
    try{await api(`/admin/service-types/${row.id}/airports`,{method:'PUT',body:JSON.stringify({expected_version:row.version,airports:list.map(item=>({code:item.code.trim().toUpperCase(),name:item.name.trim(),latitude:String(item.latitude).trim(),longitude:String(item.longitude).trim(),is_active:Boolean(item.is_active)}))})});setMessage(t('Saved.'));onSaved()}
    catch(error){if(error.code==='VERSION_CONFLICT'){setMessage(t('This service was changed. The page was reloaded; check the list and save again.'));onSaved()}else setMessage(fieldErrorText(error,t('The airports could not be saved. Please try again.')))}
    finally{setBusy(false)}
  }
  return <form className="flow-wizard-form tk-pane" onSubmit={save} noValidate>
    <p className="tk-line">{t('Passengers choose the airport from this list in Airport hire. A place within 3 km of an active airport also counts as the airport. Check each position on a map once.')}</p>
    {list.map((item,index)=><div className="tk-grid" style={{'--cols':6}} key={index}>
      <input aria-label={t('Code')} maxLength="6" value={item.code} onChange={event=>change(index,'code',event.target.value.toUpperCase())}/>
      <input aria-label={t('Airport name')} maxLength="120" value={item.name} onChange={event=>change(index,'name',event.target.value)}/>
      <input aria-label={t('Latitude')} inputMode="decimal" value={item.latitude} onChange={event=>change(index,'latitude',event.target.value)}/>
      <input aria-label={t('Longitude')} inputMode="decimal" value={item.longitude} onChange={event=>change(index,'longitude',event.target.value)}/>
      <label className="tk-line"><input type="checkbox" checked={Boolean(item.is_active)} onChange={event=>change(index,'is_active',event.target.checked)}/> {t('Active')}</label>
      <button type="button" className="ui-button ui-button-secondary" onClick={()=>setList(rows=>rows.filter((_,i)=>i!==index))}>{t('Remove')}</button>
    </div>)}
    {message&&<p className="tk-line" role="status">{message}</p>}
    <div className="flow-actions">
      <button type="button" className="ui-button ui-button-secondary" disabled={list.length>=50} onClick={()=>setList(rows=>[...rows,{code:'',name:'',latitude:'',longitude:'',is_active:true}])}>{t('Add airport')}</button>
      <button type="submit" className="ui-button ui-button-primary" disabled={busy}>{busy?t('Saving…'):t('Save airports')}</button>
    </div>
  </form>
}
