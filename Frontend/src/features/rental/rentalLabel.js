import { t } from '../../i18n/language.js'

/* "Self-drive rental · N days" for lists (03RN): booking_type RENTAL, with the days from itinerary.rental.days (bookings) or rental_days (Admin oversight). */
export const isRentalBooking=booking=>booking?.booking_type==='RENTAL'
export function rentalLabel(booking){
  const days=booking?.rental_days??booking?.itinerary?.rental?.days
  if(days==null)return t('Self-drive rental')
  return `${t('Self-drive rental')} · ${Number(days)===1?t('1 day'):t('{value0} days',{value0:days})}`
}
