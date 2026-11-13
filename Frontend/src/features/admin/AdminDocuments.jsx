import {useEffect,useState} from 'react'
import {Link} from 'react-router-dom'
import {api} from '../../services/api'
import {t} from '../../i18n/language.js'
import {displayTime,words} from '../../hooks/workspaceData'
import AdminList from './AdminList'

// First page of pending applications: the entry point to the private evidence an Admin may review.
export default function AdminDocuments(){
  const [items,setItems]=useState(null),[error,setError]=useState(null)
  useEffect(()=>{api('/admin/role-requests?status=PENDING&page=1&page_size=100').then(r=>setItems(r.items||[])).catch(setError)},[])
  return <AdminList heading={t('Document review')} title={t('Applicant documents')} icon="document" error={error} items={items}
    info={t("Open an application to review the private evidence available to your account. Document review and role approval remain separate decisions.")+' '+t("This is the first page of pending applications, not a global document queue. Continue through Users & Roles for pagination and all review statuses.")}
    empty={t('The current review queue is clear. Your own applications are excluded by the review API.')}
    footer={<Link className="ui-button ui-button-secondary" to="/admin/applications">{t('Application review')}</Link>}
    row={r=>({key:r.id,title:`${t(words(r.role_code))}${t(' application')}`,meta:`${r.applicant?.full_name||''} · ${displayTime(r.requested_at)}`,status:t('Pending review'),
      actions:<Link className="ui-button ui-button-primary" to={'/admin/applications/'+r.id}>{t('Review application')}</Link>})}/>
}
