from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

# tz_aware: datas voltam do Mongo com fuso (UTC), iguais às criadas pelos modelos.
client = AsyncIOMotorClient(settings.mongo_uri, tz_aware=True)
db = client[settings.mongo_db]
