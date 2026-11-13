/* Cash commission standing (contract 03CM): the banner kind from `commission_standing`. `blocked` is the one that decides;
   an Admin extension leaves stage BLOCKED with blocked:false, which is shown as "Extended" (banner: bookings are open until extended_until). */
export const isExtended=standing=>Boolean(standing&&standing.stage==='BLOCKED'&&!standing.blocked)
export function bannerKind(standing){
  if(!standing||!standing.stage||standing.stage==='NONE')return null
  if(standing.blocked)return 'BLOCKED'
  if(isExtended(standing))return 'EXTENDED'
  if(standing.stage==='GRACE')return 'GRACE'
  if(standing.stage==='FREE'&&Number(standing.amount_due)>0)return 'FREE'
  return null
}
export const STAGE_CHIP={NONE:['muted','No commission'],FREE:['info','Free period'],GRACE:['warning','Grace period'],BLOCKED:['danger','Blocked'],EXTENDED:['warning','Extended']}
// [tone, label key] of the stage chip.
export const stageChip=standing=>isExtended(standing)?STAGE_CHIP.EXTENDED:STAGE_CHIP[standing?.stage]||STAGE_CHIP.NONE
// Days open as [message key, params]: "Opened today" for 0, "1 day open" for 1, "{n} days open" otherwise.
export function daysOpenMessage(days){
  const n=Number(days)
  if(!Number.isFinite(n)||n<=0)return ['Opened today',{}]
  if(n===1)return ['1 day open',{}]
  return ['{value0} days open',{value0:n}]
}
// The tick "Take commission out of this payout" is offered only while the Owner owes something.
export const owesCommission=standing=>Number(standing?.amount_due)>0
export const nothingTakenOut=value=>Number(value)===0
