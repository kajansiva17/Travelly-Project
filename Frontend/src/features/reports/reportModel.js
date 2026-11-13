/* Monthly reports (contract 03RP): month helpers and small pure rules shared by the Owner and the Admin report. */
export const FIRST_MONTH='2020-01'
const pad=n=>String(n).padStart(2,'0')
// Months and "today" use Sri Lanka time (Asia/Colombo), whatever the device clock says; the API refuses a month after the current Sri Lanka month.
const COLOMBO='Asia/Colombo'
const colomboParts=date=>{const p=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:COLOMBO,year:'numeric',month:'2-digit'}).formatToParts(date).map(x=>[x.type,x.value]));return {year:Number(p.year),month:Number(p.month)}}
export const monthKey=date=>{const {year,month}=colomboParts(date);return `${year}-${pad(month)}`}
// The finished month before the current Sri Lanka month (the default of both pickers).
export function previousMonth(now=new Date()){const {year,month}=colomboParts(now);return month===1?`${year-1}-12`:`${year}-${pad(month-1)}`}
// The picker cannot go past this month and the API starts in 2020.
export const thisMonth=(now=new Date())=>monthKey(now)
export const validPeriod=(value,now=new Date())=>/^\d{4}-(0[1-9]|1[0-2])$/.test(value||'')&&value>=FIRST_MONTH&&value<=thisMonth(now)
export const pdfName=(period,admin=false)=>`travelly-${admin?'admin-':''}report-${period}.pdf`
const num=value=>{const n=Number(value);return Number.isFinite(n)?n:0}
// Loss: the contract's `is_loss` decides; without it the sign of the profit does.
export const isLoss=result=>typeof result?.is_loss==='boolean'?result.is_loss:num(result?.profit)<0
export const attentionTone=count=>num(count)>0?'danger':'muted'
// Admin tile "bookings": private hire (Event hire is counted there), ticket and rental bookings made in the month.
export const bookingsMade=summary=>num(summary?.private_hire_bookings)+num(summary?.ticket_bookings)+num(summary?.rental_bookings)
export const hasRows=list=>Array.isArray(list)&&list.length>0
