/* Notifications are matched by notification_type and action_payload keys, never by title or body wording (contract 03N).
   GET /notifications returns notification_type, action_payload, action_required, booking_id, trip_id, scheduled_trip_id,
   created_at, read_at and expires_at. Unknown payload keys are ignored. */
export const noticeBookingId=note=>note?.booking_id||note?.action_payload?.booking_id||null
// Replacement vehicle waiting for the Passenger's answer: REPLACEMENT with action_required. It opens the booking's change card.
export const isReplacementAction=note=>note?.notification_type==='REPLACEMENT'&&note.action_required===true&&Boolean(noticeBookingId(note))
// "We are arranging your journey" and the other replacement notices that need no answer.
export const isReplacementInfo=note=>note?.notification_type==='REPLACEMENT'&&note.action_required!==true
export const isRefundNotice=note=>note?.notification_type==='REFUND'
export const isRoadAlertNotice=note=>note?.notification_type==='ROAD_ALERT'
// A notification whose expires_at has passed (a ROAD_ALERT then shows greyed, as "Expired").
export const isExpired=(note,now=Date.now())=>Boolean(note?.expires_at)&&new Date(note.expires_at).getTime()<now
