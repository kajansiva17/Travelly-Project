import {publicRead,publicRequest} from '../../services/api'

/* Travelly AI (contract 03AI). Every endpoint is public, so these calls carry no sign-in and work signed in or out.
   Nothing is stored, held or booked by the AI. */
export const searchAssist=({message,language,filters,asking})=>publicRequest('/ai/search-assist',{message,language,filters:filters||{},asking:asking||null})
export const askHelp=({question,language})=>publicRequest('/ai/help',{question,language})
export const helpTopics=language=>publicRead(`/ai/help/topics/${language}`)
