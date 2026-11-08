import { t } from '../i18n/language.js'
import React from 'react'
import {Link} from 'react-router-dom'
import {useWorkspace} from '../context/workspaceContext'

export default function ApplicationStatusNotices({all=false}){
 const {roles,allowed}=useWorkspace()
 return roles.filter(row=>['OWNER','DRIVER'].includes(row.role_code)&&(all||row.approval_status==='REJECTED')).map(row=><section className="workspace-card application-status-notice" key={row.role_code} role="status"><div><strong>{row.role_code==='OWNER'?t('Owner'):t('Driver')}{t(" application: ")}{t(row.approval_status.toLowerCase())}</strong>{row.approval_status==='REJECTED'&&<p>{row.rejection_reason||t('Review your application for the decision details.')}</p>}</div><Link className="button outline" to={allowed.includes(row.role_code)?`/${row.role_code.toLowerCase()}/dashboard`:`/${row.role_code.toLowerCase()}/onboarding`}>{allowed.includes(row.role_code)?t('Open dashboard'):t('View application')}</Link></section>)
}
