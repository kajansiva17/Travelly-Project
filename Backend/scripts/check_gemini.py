"""Replaced by check_ai.py, which checks Groq, OpenRouter and Gemini. Kept so old notes still work."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name('check_ai.py')), run_name='__main__')
