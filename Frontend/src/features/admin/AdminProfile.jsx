import { t } from '../../i18n/language.js'
import {useEffect,useRef,useState} from 'react'
import {api} from '../../services/api'
import {ErrorNotice,Icon} from '../../components/components'
import {useWorkspace} from '../../context/workspaceContext'
import {FlowShell} from '../booking/flow/FlowParts'
import ProfileAuth from '../auth/ProfileAuth'
import {fieldErrors} from '../../services/fieldErrors.js'

const draftFor=user=>({full_name:user.full_name,phone_e164:user.phone_e164||'',profile_image_url:user.profile_image_url||null})

export default function AdminProfile({user,onSaved,error:loadError}){
 const [tab,setTab]=useState(0),workspace=useWorkspace(),file=useRef(null),name=useRef(null),phone=useRef(null),selection=useRef(0)
 const [draft,setDraft]=useState(()=>user?draftFor(user):null),[editing,setEditing]=useState({}),[busy,setBusy]=useState(false),[reading,setReading]=useState(false),[error,setError]=useState(null),[message,setMessage]=useState('')
 useEffect(()=>{if(user)setDraft(draftFor(user))},[user])
 useEffect(()=>()=>{selection.current++},[])
 const changed=user&&draft&&JSON.stringify(draft)!==JSON.stringify(draftFor(user))
 function cancel(){selection.current++;setReading(false);setDraft(draftFor(user));setEditing({});setError(null);setMessage('');if(file.current)file.current.value=''}
 function edit(field,ref){setEditing(value=>({...value,[field]:true}));setMessage('');requestAnimationFrame(()=>ref.current?.focus())}
 async function upload(event){
  const image=event.target.files?.[0],ticket=++selection.current
  if(!image)return
  setError(null);setMessage('')
  if(!['image/jpeg','image/png','image/webp'].includes(image.type)||image.size>1048576){setError(new Error('Choose a JPEG, PNG or WebP image up to 1 MB.'));event.target.value='';return}
  setReading(true)
  try{const value=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(new Error('Unable to read this image.'));reader.readAsDataURL(image)});if(ticket===selection.current)setDraft(current=>({...current,profile_image_url:value}))}
  catch(err){if(ticket===selection.current)setError(err)}finally{if(ticket===selection.current)setReading(false);if(file.current)file.current.value=''}
 }
 async function save(event){
  event.preventDefault();if(busy||reading||!changed)return
  setBusy(true);setError(null);setMessage('')
  try{const result=await api('/users/me',{method:'PATCH',body:JSON.stringify({...draft,full_name:draft.full_name.trim(),phone_e164:draft.phone_e164.trim()||null,version:user.version})});onSaved(result);workspace.updateProfile(result);setEditing({});setMessage('Your profile has been updated.')}
  catch(err){setError(err)}finally{setBusy(false)}
 }
 return <FlowShell heading={t("Profile")} title={tab===0?t("Personal profile"):t("Account security")} icon="user" info={tab===0?t("Manage your personal information."):t("Your sign-in methods and email verification. Phone verification is separate.")} tabs={[{label:t("Profile details"),active:tab===0,onClick:()=>setTab(0),icon:'user'},{label:t("Account security"),active:tab===1,onClick:()=>setTab(1),icon:'shield'}]}>
  <ErrorNotice error={loadError}/>{!user||!draft?!loadError&&<p role="status">{t("Loading your profile…")}</p>:<>
  <form className="admin-profile-card flow-wizard-form" hidden={tab!==0} onSubmit={save} aria-label={t("Personal profile")}>
   <div className="admin-profile-photo"><div className="admin-profile-avatar">{draft.profile_image_url?<img src={draft.profile_image_url} alt={t("Your profile")} referrerPolicy="no-referrer"/>:<span aria-label={t("Profile initials")}>{Array.from(draft.full_name.trim()||user.full_name)[0]}</span>}</div><div><h2>{t("Profile picture")}</h2><p>{t("JPEG, PNG or WebP · Up to 1 MB")}</p><div className="admin-photo-actions"><button type="button" className="button outline" onClick={()=>file.current.click()} disabled={busy||reading}><Icon name="upload" size={16}/>{draft.profile_image_url?t('Change photo'):t('Upload photo')}</button>{draft.profile_image_url&&<button type="button" className="admin-profile-text-button" disabled={busy||reading} onClick={()=>{selection.current++;setDraft(current=>({...current,profile_image_url:null}));setMessage('')}}>{t("Remove photo")}</button>}</div><input ref={file} type="file" accept="image/jpeg,image/png,image/webp" aria-label={t("Upload profile picture")} hidden onChange={upload}/></div></div>
   <ErrorNotice error={error}/>{fieldErrors(error).map(field=><p key={field.field} className="field-error">{t(field.message)}</p>)}{message&&<p className="admin-profile-success" role="status">{t(message)}</p>}
   <fieldset disabled={busy||reading} className="admin-profile-fields"><div className="admin-profile-field"><div className="admin-profile-label"><label htmlFor="admin-profile-name">{t("Full name")}</label><button type="button" className="admin-profile-text-button" onClick={()=>edit('full_name',name)} aria-label={t("Edit full name")}>{t("Edit")}</button></div><input id="admin-profile-name" ref={name} autoComplete="name" maxLength={150} required readOnly={!editing.full_name} value={draft.full_name} onChange={e=>setDraft({...draft,full_name:e.target.value})}/></div>
   <div className="admin-profile-field"><span className="admin-profile-label">{t("Email address")}</span><p className="admin-profile-value">{user.email||t('Not provided')}</p></div>
   <div className="admin-profile-field"><div className="admin-profile-label"><label htmlFor="admin-profile-phone">{t("Mobile number")}</label><button type="button" className="admin-profile-text-button" onClick={()=>edit('phone_e164',phone)} aria-label={t("Edit mobile number")}>{t("Edit")}</button></div><input id="admin-profile-phone" ref={phone} type="tel" autoComplete="tel" maxLength={25} placeholder={t("Include country code, e.g. +94")} readOnly={!editing.phone_e164} value={draft.phone_e164} onChange={e=>setDraft({...draft,phone_e164:e.target.value})}/></div>
   <div className="admin-profile-field"><span className="admin-profile-label">{t("Account role")}</span><p className="admin-profile-value"><span className="admin-role-badge"><Icon name="shield" size={15}/>{t("Super Admin")}</span></p></div></fieldset>
   <div className="admin-profile-footer flow-actions"><button type="button" className="button outline" onClick={cancel} disabled={busy||reading||(!changed&&!Object.values(editing).some(Boolean))}>{t("Cancel")}</button><button type="submit" className="button admin-profile-save" disabled={busy||reading||!changed}>{busy?t('Saving…'):reading?t('Reading image…'):t('Save Changes')}</button></div>
  </form>
  <div className="flow-wizard-form" hidden={tab!==1}><ProfileAuth user={user}/></div></>}
 </FlowShell>
}
