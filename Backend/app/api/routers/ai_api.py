"""Travelly AI (PRD matrix 90-91 and D10; help assistant owner decision 12 Nov 2026).

    POST /ai/search-assist          one chat or voice turn: fills the search form fields, asks for the next missing one
    POST /ai/help                   "how do I ...?" answered only from the Travelly help guide, with a page link
    GET  /ai/help/topics/{language} every help topic, for a "What can I ask?" list

Signed-in customers only (owner decision 13 Nov 2026: PRD D10 allows public AI, but a public page would use up the free
Gemini quota). Each person has a daily Gemini cap, then the built-in rules answer. The topic list stays public.
Nothing is stored and nothing is booked: the person checks the filled form and presses Search, which calls the normal search endpoints, so
only real, eligible vehicles and departures appear. Rate-limited per person.
"""
from typing import Literal
from fastapi import APIRouter, Depends, Request
from app.api.routers.api import current
from app.core.config import get_settings
from app.schemas.ai_schemas import HelpQuestion, SearchAssist
from app.services import ai_assist

router = APIRouter(prefix='/api/v1', tags=['ai'])


@router.post('/ai/search-assist')
def search_assist(body: SearchAssist, request: Request, user=Depends(current)):
    request.app.state.store.rate(f'ai-search:{user.id}', 60, 600)
    known = body.filters.model_dump(exclude_none=True)
    return ai_assist.search_assist(get_settings(), request.app.state.store, body.message, body.language, known, body.asking,
                                   user_id=user.id)


@router.post('/ai/help')
def help_question(body: HelpQuestion, request: Request, user=Depends(current)):
    request.app.state.store.rate(f'ai-help:{user.id}', 30, 600)
    return ai_assist.help_answer(get_settings(), request.app.state.store, body.question, body.language, user_id=user.id)


@router.get('/ai/help/topics/{language}')
def help_topics(language: Literal['en', 'ta', 'si']):
    return {'items': ai_assist.topics(language)}
