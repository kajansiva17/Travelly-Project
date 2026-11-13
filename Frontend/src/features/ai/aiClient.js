/* Travelly AI requests (contract 03AI). Signed-in customers only: every call goes through the app's normal API client, which sends the
   Bearer token and handles an expired session (renew, or end the session) exactly as every other screen does. Nothing is stored,
   held or booked by the AI. The client is passed in so the paths and bodies can be tested without a browser. */
export function createAiRequests(client){
  return {
    searchAssist:({message,language,filters,asking})=>client('/ai/search-assist',{method:'POST',body:JSON.stringify({message,language,filters:filters||{},asking:asking||null})}),
    askHelp:({question,language})=>client('/ai/help',{method:'POST',body:JSON.stringify({question,language})}),
    helpTopics:language=>client(`/ai/help/topics/${language}`)
  }
}
