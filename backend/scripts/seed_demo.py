"""Popula o MongoDB configurado (.env) com os dados de demonstração.

Uso, a partir de backend/:
    .venv/Scripts/python -m scripts.seed_demo            # grava (idempotente)
    .venv/Scripts/python -m scripts.seed_demo --reset    # apaga só os dados demo- e regrava
"""

import argparse
import asyncio
import sys

from app.core.config import settings
from app.db import collections, mongodb
from app.db.demo_seed import seed_demo

_ROTULOS = {
    collections.SCRIPTS: "roteiros",
    collections.PARTICIPANTS: "participantes",
    collections.SESSIONS: "sessões",
    collections.SYNTHESES: "sínteses",
}


async def main(reset: bool) -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # console do Windows usa cp1252
    print(f"Banco: {settings.mongo_db}" + (" (reset dos dados demo-)" if reset else ""))
    counts = await seed_demo(mongodb.db, reset=reset)
    for colecao, total in counts.items():
        print(f"  {_ROTULOS[colecao]}: {total}")
    print("Dados de demonstração gravados. Dados reais não foram alterados.")
    mongodb.client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="apaga antes só os documentos demo-")
    asyncio.run(main(parser.parse_args().reset))
