/* Travel Reels (contract 03SO): small pure helpers for the feed. */
export const TABS=[['REEL','Reels'],['PHOTO','Photos'],['REVIEW','Reviews'],['FOLLOWING','Following']]
export const VISIBILITY=[['PUBLIC','Everyone'],['FOLLOWERS','Followers'],['PRIVATE','Only me']]
export const PAGE_SIZE=20

// GET /social/feed query for a tab. Following has no filter in the contract: it reads every type and keeps the followed authors.
export function feedQuery({tab,hashtag='',before='',limit=PAGE_SIZE,author=''}){
  const q=new URLSearchParams()
  if(tab&&tab!=='FOLLOWING')q.set('type',tab)
  if(hashtag)q.set('hashtag',hashtag.replace(/^#/,''))
  if(author)q.set('author',author)
  if(before)q.set('before',before)
  q.set('limit',String(limit))
  return q.toString()
}
export const visibleInTab=(tab,item)=>tab!=='FOLLOWING'||Boolean(item.following_author)
export const viewsOf=item=>Number(item?.view_count||0)
export const ratingOf=item=>Math.max(0,Math.min(5,Math.round(Number(item?.rating||0))))
// After a follow change, every loaded post of that author follows.
export const withFollow=(items,reference,active)=>items.map(item=>item.author?.reference===reference?{...item,following_author:active}:item)
export const replaceItem=(items,next)=>items.map(item=>item.id===next.id?{...item,...next}:item)
export const sharePath=(origin,path)=>String(origin||'').replace(/\/$/,'')+path
// Hashtags typed as "ella, #beach" become ["ella","beach"].
export const parseTags=text=>[...new Set(String(text||'').split(/[,\s]+/).map(tag=>tag.replace(/^#/,'').trim()).filter(Boolean))]
