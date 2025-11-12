# Entry-point for: python -m bot.bot
from .app import _run_polling
import asyncio
if __name__ == "__main__":
    asyncio.run(_run_polling())