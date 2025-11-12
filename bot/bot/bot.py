# Module for: python -m bot.bot
from .app import _run_polling
import asyncio
def main():
    asyncio.run(_run_polling())
if __name__ == "__main__":
    main()