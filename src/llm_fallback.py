"""Stub: LLM fallback was removed by configuration.

Kept as a placeholder so the file path stays consistent if you change your mind
and want to add fallback later. To re-enable:

1. Add `anthropic>=0.34.0` to requirements.txt
2. Add ANTHROPIC_API_KEY to .env.example, config.py, and the workflow
3. Restore the Anthropic call in this module
4. In horoscope_loader.py, wrap the scraper call in try/except and call
   `generate_horoscope(zodiac)` on failure instead of raising SkipDay
"""
