import {mediaUrl} from '../../services/api'

// media_url / thumbnail_url exactly as given (signed ?t= links included), only the API address in front.
export const src=url=>url?mediaUrl(url):''
