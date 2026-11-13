"""Check every AI service set in Backend/.env (Groq, OpenRouter, Gemini), one by one, without printing any key.

Run from the project folder:
    .venv\\Scripts\\python.exe Backend\\scripts\\check_ai.py
For each service with a key it sends one short test sentence and prints YES or NO with the reason. Chat, search and
help try the services in AI_PROVIDERS order; the odometer photo uses AI_VISION_PROVIDERS.
"""
import os
import sys
from datetime import datetime
from pathlib import Path

backend = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend))
os.chdir(backend)  # so Backend/.env is read

from app.core.config import get_settings  # noqa: E402
from app.services import ai_assist  # noqa: E402

settings = get_settings()
secrets = [settings.groq_api_key, settings.openrouter_api_key, settings.gemini_api_key]
models = {'groq': settings.groq_model, 'openrouter': settings.openrouter_model, 'gemini': settings.gemini_model}
print('Order for chat/search/help:', settings.ai_providers)
print('Order for odometer photo:  ', settings.ai_vision_providers, f'(OpenRouter photo model: {settings.openrouter_vision_model})')
prompt = ('Read this traveller message and return JSON with pickup, destination and passengers only. '
          'Message: naalai Kandy-la irunthu Colombo-kku 4 per')
schema = {'type': 'OBJECT', 'properties': {'pickup': {'type': 'STRING'}, 'destination': {'type': 'STRING'}, 'passengers': {'type': 'INTEGER'}}}
for name, field in ai_assist.KEYS.items():
    has_key = bool(getattr(settings, field).strip())
    if not has_key:
        print(f'{name:<11} key set: NO  (skipped)')
        continue
    try:
        answer = ai_assist.call(name, settings, prompt, schema)
        print(f'{name:<11} key set: YES  model {models[name]}  -> answered: YES {answer}')
    except Exception as exc:  # noqa: BLE001 - show the reason, never a key
        message = str(exc)
        for secret in secrets:
            if secret.strip():
                message = message.replace(secret, '***')
        print(f'{name:<11} key set: YES  model {models[name]}  -> answered: NO  {message[:200]}')
if not ai_assist.providers(settings):
    print('No AI key is set: the built-in rules will answer (the app still works).')
