"""Check that the Gemini key in Backend/.env works, without printing it.

Run from the project folder:
    .venv\\Scripts\\python.exe Backend\\scripts\\check_gemini.py
It sends one short test sentence to Gemini and prints what the smart search understood.
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
print('GEMINI_API_KEY set:', bool(settings.gemini_api_key.strip()))
print('Model:             ', settings.gemini_model)
if not settings.gemini_api_key.strip():
    sys.exit('Add GEMINI_API_KEY to Backend/.env, then run this again.')
try:
    found = ai_assist.gemini_extract(settings, 'naalai kaalai 8 mani Kandy-la irunthu Colombo-kku 4 per', None, {},
                                     datetime.now(ai_assist.ZONE))
    print('Gemini answered: YES -', found)
except Exception as exc:  # noqa: BLE001 - show the reason, never the key
    print('Gemini answered: NO -', str(exc).replace(settings.gemini_api_key, '***'))
