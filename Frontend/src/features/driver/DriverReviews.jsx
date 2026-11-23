import { useEffect, useState } from 'react'
import { t } from '../../i18n/language.js'
import { api } from '../../services/api'
import { Header, ErrorNotice } from '../../components/components'
import { FlowShell } from '../booking/flow/FlowParts'
import { displayTime } from '../../hooks/workspaceData'
import { stars } from '../trips/RateTrip'

/* Driver > My reviews: what Passengers rated about the driving after their trips (GET /drivers/me/reviews). Read only. */
export default function DriverReviews() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => { api('/drivers/me/reviews', { cache: 'no-store' }).then(setData).catch(setError) }, [])
  return <><Header/><FlowShell heading={t('My reviews')} title={t('What Passengers say about your driving')} icon="star"
    info={t('Passengers can rate the Driver after a trip. You see the rating, the comment and the first name of the Passenger.')}>
    <ErrorNotice error={error}/>
    {!data && !error && <p role="status">{t('Loading…')}</p>}
    {data && !data.count && <p className="flow-note" role="status">{t('No reviews yet.')}</p>}
    {data && data.count > 0 && <>
      <p><strong style={{ fontSize: 22, color: '#f5a623' }}>{stars(Math.round(Number(data.average)))}</strong>{' '}<strong>{data.average}</strong>{' · '}{t('{value0} reviews', { value0: data.count })}</p>
      {data.items.map(item => <article className="tk-row" key={item.id} style={{ display: 'block' }}>
        <div className="tk-row-main"><strong style={{ color: '#f5a623' }}>{stars(item.driver_rating)}</strong>
          <span>{item.passenger ? item.passenger + ' · ' : ''}{item.trip_reference}{' · '}{displayTime(item.created_at)}</span></div>
        {item.comment && <p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{item.comment}</p>}
      </article>)}
    </>}
  </FlowShell></>
}
