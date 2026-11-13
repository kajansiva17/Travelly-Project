/* Cash commission standing (contract 03CM): the banner kind from `commission_standing`. `blocked` is the one that decides;
   an Admin extension can leave stage BLOCKED with blocked:false, which is shown as the grace warning. */
export function bannerKind(standing){
  if(!standing||!standing.stage||standing.stage==='NONE')return null
  if(standing.blocked)return 'BLOCKED'
  if(standing.stage==='GRACE'||standing.stage==='BLOCKED')return 'GRACE'
  if(standing.stage==='FREE'&&Number(standing.amount_due)>0)return 'FREE'
  return null
}
export const STAGE_CHIP={NONE:['muted','No commission'],FREE:['info','Free period'],GRACE:['warning','Grace period'],BLOCKED:['danger','Blocked']}
