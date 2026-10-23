"""Database layer. MONGODB_URI thakle MongoDB, na thakle in-memory (demo/test)."""
import copy
import uuid
from datetime import datetime, timezone

from .config import settings


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryDB:
    kind = "memory"

    def __init__(self):
        self.c = {}

    async def setup(self):
        pass

    async def insert(self, coll, doc):
        self.c.setdefault(coll, {})[doc["id"]] = copy.deepcopy(doc)
        return doc

    async def get(self, coll, id):
        d = self.c.get(coll, {}).get(id)
        return copy.deepcopy(d) if d else None

    async def list(self, coll, flt=None, limit=200):
        out = [copy.deepcopy(d) for d in self.c.get(coll, {}).values()
               if all(d.get(k) == v for k, v in (flt or {}).items())]
        return out[::-1][:limit]

    async def update(self, coll, id, fields):
        d = self.c.get(coll, {}).get(id)
        if d is None:
            return None
        d.update(copy.deepcopy(fields))
        return copy.deepcopy(d)

    async def ping(self):
        return True


class MongoDB:
    kind = "mongodb"
    COLLECTIONS = ["farmers", "buyers", "lots", "demands", "batches", "orders", "prices", "users", "watches"]

    def __init__(self, uri, name):
        from motor.motor_asyncio import AsyncIOMotorClient
        self.client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=8000)
        self.db = self.client[name]

    async def setup(self):
        for c in self.COLLECTIONS:
            await self.db[c].create_index("id", unique=True)
        await self.db["users"].create_index("phone", unique=True)

    async def insert(self, coll, doc):
        await self.db[coll].insert_one(dict(doc))
        return doc

    async def get(self, coll, id):
        return await self.db[coll].find_one({"id": id}, {"_id": 0})

    async def list(self, coll, flt=None, limit=200):
        cur = self.db[coll].find(flt or {}, {"_id": 0}).sort("created_at", -1).limit(limit)
        return await cur.to_list(limit)

    async def update(self, coll, id, fields):
        from pymongo import ReturnDocument
        return await self.db[coll].find_one_and_update(
            {"id": id}, {"$set": fields}, return_document=ReturnDocument.AFTER, projection={"_id": 0})

    async def ping(self):
        await self.client.admin.command("ping")
        return True


def make_db():
    if settings.MONGODB_URI:
        return MongoDB(settings.MONGODB_URI, settings.MONGODB_DB)
    return MemoryDB()
