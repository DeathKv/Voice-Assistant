import asyncio
import threading
from gemini_client import main as gemini_main
from web_server import start_server

async def run_everything():
    # Roda o servidor WebSocket e a Aria lado a lado
    await asyncio.gather(
        start_server(),
        gemini_main()
    )

if __name__ == "__main__":
    try:
        asyncio.run(run_everything())
    except KeyboardInterrupt:
        print("\n👋 Encerrado.")