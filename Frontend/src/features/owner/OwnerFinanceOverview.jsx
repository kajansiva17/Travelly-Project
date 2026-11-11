import { t } from '../../i18n/language.js'
import React,{useEffect,useState} from 'react'
import {Link} from 'react-router-dom'
import {api} from '../../services/api'
import {Header,ErrorNotice} from '../../components/components'
import {TravellyGlassPanel,TravellyState,TravellyStatusChip} from '../../components/TravellyVisualFoundation'
import {FlowShell,useRowCount,usePaged} from '../booking/flow/FlowParts'
export default function OwnerFinanceOverview(){const [items,setItems]=useState(null),[error,setError]=useState(null);useEffect(()=>{api('/bookings').then(x=>setItems(x.items||[])).catch(setError)},[]);const paged=usePaged(items,useRowCount(60));return <><Header/><FlowShell heading="Finance" title="Trip profitability and settlements" icon="wallet" info="Only real finalized trip finance records are shown. Travelly does not hold funds or initiate payouts."><ErrorNotice error={error}/>{items===null?<TravellyState kind="loading" title="Loading accessible booking records"/>:items.length?<div className="workspace-record-list">{paged.slice.map(x=><article key={x.id} className="workspace-record"><div><strong>{x.reference}</strong><span>{x.status?.replaceAll('_',' ')}</span></div><Link className="button outline" to={`/bookings/${x.id}?workspace=owner`}>{t('Open booking')}</Link></article>)}</div>:<TravellyState title="No completed settlement records">{t('Settlement and profitability appear only after a real finalized trip/payment record exists.')}</TravellyState>}{items&&items.length>0&&<div className="flow-actions"><span/>{paged.pager}</div>}</FlowShell></>}
