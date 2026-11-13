import {api} from '../../services/api'
import {createAiRequests} from './aiClient'

export const {searchAssist,askHelp,helpTopics}=createAiRequests(api)
