/* Event packages (contract 03EV): checks and the PUT body. A package is a name, the hours and a fixed price (vehicle + Driver). Pure. */
export const PACKAGE_LIMITS={min:1,max:20,name:120,notes:500,maxHours:24}
const decimals=text=>{const m=String(text).trim().match(/^\d+(?:\.(\d+))?$/);return m?(m[1]||'').length:-1}
// Field errors of one package draft: { name?, hours?, price?, notes? } with message codes, {} when fine.
export function checkPackage(p){
  const e={},name=String(p.name||'').trim(),hours=Number(p.hours),price=Number(p.price)
  if(!name||name.length>PACKAGE_LIMITS.name)e.name='NAME'
  if(String(p.hours||'').trim()===''||!(hours>0)||hours>PACKAGE_LIMITS.maxHours)e.hours='HOURS'
  if(String(p.price||'').trim()===''||!(price>0)||decimals(p.price)<0||decimals(p.price)>2)e.price='PRICE'
  if(String(p.notes||'').length>PACKAGE_LIMITS.notes)e.notes='NOTES'
  return e
}
export const canSave=list=>list.length>=PACKAGE_LIMITS.min&&list.length<=PACKAGE_LIMITS.max&&list.every(p=>!Object.keys(checkPackage(p)).length)
export const newPackageId=()=>globalThis.crypto?.randomUUID?globalThis.crypto.randomUUID():'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,c=>{const r=Math.random()*16|0;return (c==='x'?r:(r&3|8)).toString(16)})
// Hours stay as typed (trimmed, "6" or "6.5"); the price always has two decimals; empty notes are left out. The id of an edited package is kept.
export function toBody({serviceTypeId,version,enabled,packages}){
  return {service_type_id:serviceTypeId,expected_version:version,enabled:Boolean(enabled),packages:packages.map(p=>{
    const notes=String(p.notes||'').trim()
    return {id:p.id,name:String(p.name).trim(),hours:String(p.hours).trim(),price:Number(p.price).toFixed(2),...(notes?{notes}:{})}})}
}
// The saved packages from GET /vehicles/{id}/services (Event row: event_packages), or none yet (version 0).
export function readEvent(items,serviceTypeId){
  const row=(items||[]).find(r=>r.service_type_id===serviceTypeId)
  return {version:row?.version??0,enabled:row?.enabled??true,packages:(row?.event_packages||[]).map(p=>({id:p.id,name:p.name,hours:String(p.hours),price:String(p.price),notes:p.notes||''}))}
}
