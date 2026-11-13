/* Monthly reports (contract 03RP): month helpers and small pure rules shared by the Owner and the Admin report. */
export const FIRST_MONTH='2020-01'
const pad=n=>String(n).padStart(2,'0')
export const monthKey=date=>`${date.getFullYear()}-${pad(date.getMonth()+1)}`
// The finished month before `now` (the default of both pickers).
export function previousMonth(now=new Date()){return monthKey(new Date(now.getFullYear(),now.getMonth()-1,1))}
// The picker cannot go past this month and the API starts in 2020.
export const thisMonth=(now=new Date())=>monthKey(now)
export const validPeriod=(value,now=new Date())=>/^\d{4}-(0[1-9]|1[0-2])$/.test(value||'')&&value>=FIRST_MONTH&&value<=thisMonth(now)
export const pdfName=(period,admin=false)=>`travelly-${admin?'admin-':''}report-${period}.pdf`
const num=value=>{const n=Number(value);return Number.isFinite(n)?n:0}
// Loss: the contract's `is_loss` decides; without it the sign of the profit does.
export const isLoss=result=>typeof result?.is_loss==='boolean'?result.is_loss:num(result?.profit)<0
export const attentionTone=count=>num(count)>0?'danger':'muted'
// Admin tile "bookings": private hire and ticket bookings made in the month.
export const bookingsMade=summary=>num(summary?.private_hire_bookings)+num(summary?.ticket_bookings)
export const hasRows=list=>Array.isArray(list)&&list.length>0
