import {parseTags} from './socialModel.js'

/* Creating a post (contract 03SO, section 1): limits, checks and the multipart form. Pure, so it can be tested. */
export const LIMITS={reelSeconds:60,reelBytes:50*1024*1024,reelMb:50,caption:2200,hashtags:30,place:160}
export const VIDEO_TYPES=['video/mp4','video/quicktime','video/webm']
export const POST_TYPES=[['REEL','Reel','video'],['PHOTO','Photo','star'],['REVIEW','Review','chat']]
// '' when fine, otherwise a code: TOO_LARGE (over 50 MB), WRONG_TYPE.
export function checkVideoFile(file){
  if(!file)return 'MISSING'
  if(file.size>LIMITS.reelBytes)return 'TOO_LARGE'
  if(file.type&&!VIDEO_TYPES.includes(file.type))return 'WRONG_TYPE'
  return ''
}
// '' when fine; TOO_LONG over 60 seconds; UNREADABLE when the browser could not read a length.
export function checkDuration(seconds){
  if(!Number.isFinite(seconds)||seconds<=0)return 'UNREADABLE'
  return seconds>LIMITS.reelSeconds?'TOO_LONG':''
}
export const wholeSeconds=seconds=>Math.max(1,Math.min(LIMITS.reelSeconds,Math.ceil(seconds)))
// Frame size for the thumbnail: the video's own shape, at most `max` on the long side.
export function thumbSize(width,height,max=720){
  if(!width||!height)return {width:0,height:0}
  const scale=Math.min(1,max/Math.max(width,height))
  return {width:Math.round(width*scale),height:Math.round(height*scale)}
}
// Everything that stops the Post button, as a list of codes (empty = ready).
export function problems(v){
  const out=[]
  if(!v.visibility)out.push('visibility')
  if(v.post_type==='REEL'){if(!v.file||checkVideoFile(v.file)||checkDuration(v.duration))out.push('file')}
  if(v.post_type==='PHOTO'&&!v.file)out.push('file')
  if(v.post_type==='REVIEW'){if(!v.linked_vehicle_id)out.push('linked_vehicle_id');if(!(v.rating>=1&&v.rating<=5))out.push('rating');if(!String(v.caption||'').trim())out.push('caption')}
  if(String(v.caption||'').length>LIMITS.caption)out.push('caption')
  if(parseTags(v.hashtags).length>LIMITS.hashtags)out.push('hashtags')
  return out
}
// The multipart body for POST /social/posts. Optional fields that are empty are left out.
export function buildPostForm(v){
  const form=new FormData()
  form.append('post_type',v.post_type)
  form.append('visibility',v.visibility)
  if(v.file)form.append('file',v.file,v.file.name||'upload')
  if(v.post_type==='REEL'){
    if(v.thumbnail)form.append('thumbnail',v.thumbnail,'thumbnail.jpg')
    form.append('duration_seconds',String(wholeSeconds(v.duration)))
  }
  const caption=String(v.caption||'').trim();if(caption)form.append('caption',caption)
  const tags=parseTags(v.hashtags);if(tags.length)form.append('hashtags',JSON.stringify(tags))
  const place=String(v.location_name||'').trim();if(place)form.append('location_name',place)
  if(v.post_type==='REVIEW'){form.append('linked_vehicle_id',v.linked_vehicle_id);form.append('rating',String(v.rating))}
  return form
}
