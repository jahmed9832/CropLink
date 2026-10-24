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
        if coll == "users" and "phone" in doc:
            for u in self.c.get("users", {}).values():
                if u.get("phone") == doc["phone"]:
                    raise ValueError(f"Duplicate key error: phone '{doc['phone']}' already exists")
        self.c.setdefault(coll, {})[doc["id"]] = copy.deepcopy(doc)
        return doc

    async def delete(self, coll, id):
        if coll in self.c and id in self.c[coll]:
            del self.c[coll][id]
            return True
        return False

    async def get(self, coll, id):
        d = self.c.get(coll, {}).get(id)
        return copy.deepcopy(d) if d else None

    async def list(self, coll, flt=None, limit=200, skip=0):
        items = list(self.c.get(coll, {}).values())
        def _match_field(doc, k, v):
            if k == "allocations.farmer_id":
                allocs = doc.get("allocations") or []
                return any(isinstance(a, dict) and a.get("farmer_id") == v for a in allocs)
            if "." in k:
                parts = k.split(".")
                curr = doc
                for p in parts:
                    if not isinstance(curr, dict) or p not in curr:
                        return False
                    curr = curr[p]
                return curr == v
            return doc.get(k) == v

        out = [copy.deepcopy(d) for d in items
               if all(_match_field(d, k, v) for k, v in (flt or {}).items())]
        # Stable sort by created_at descending if present
        out.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        return out[skip:skip + limit]

    async def update(self, coll, id, fields):
        d = self.c.get(coll, {}).get(id)
        if d is None:
            return None
        for k, v in fields.items():
            if "." in k:
                parts = k.split(".")
                curr = d
                for p in parts[:-1]:
                    curr = curr.setdefault(p, {})
                curr[parts[-1]] = copy.deepcopy(v)
            else:
                d[k] = copy.deepcopy(v)
        return copy.deepcopy(d)

    async def update_if(self, coll, id, expected: dict, fields: dict):
        d = self.c.get(coll, {}).get(id)
        if d is None:
            return None
        for k, v in expected.items():
            if "." in k:
                parts = k.split(".")
                curr = d
                for p in parts:
                    if isinstance(curr, dict) and p in curr:
                        curr = curr[p]
                    else:
                        curr = None
                        break
                if curr != v:
                    return None
            else:
                if d.get(k) != v:
                    return None
        for k, v in fields.items():
            if "." in k:
                parts = k.split(".")
                curr = d
                for p in parts[:-1]:
                    curr = curr.setdefault(p, {})
                curr[parts[-1]] = copy.deepcopy(v)
            else:
                d[k] = copy.deepcopy(v)
        return copy.deepcopy(d)

    async def ping(self):
        return True

    async def close(self):
        pass


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
        # Indexes for queries
        await self.db["lots"].create_index([("crop", 1), ("status", 1)])
        await self.db["lots"].create_index("farmer_id")
        await self.db["demands"].create_index([("crop", 1), ("status", 1)])
        await self.db["demands"].create_index("buyer_id")
        await self.db["orders"].create_index("buyer_id")
        await self.db["orders"].create_index("allocations.farmer_id")
        await self.db["orders"].create_index([("crop", 1), ("status", 1)])

    async def insert(self, coll, doc):
        await self.db[coll].insert_one(dict(doc))
        return doc

    async def get(self, coll, id):
        return await self.db[coll].find_one({"id": id}, {"_id": 0})

    async def list(self, coll, flt=None, limit=200, skip=0):
        cur = self.db[coll].find(flt or {}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
        return await cur.to_list(limit)

    async def update(self, coll, id, fields):
        from pymongo import ReturnDocument
        return await self.db[coll].find_one_and_update(
            {"id": id}, {"$set": fields}, return_document=ReturnDocument.AFTER, projection={"_id": 0})

    async def update_if(self, coll, id, expected: dict, fields: dict):
        from pymongo import ReturnDocument
        query = {"id": id, **expected}
        return await self.db[coll].find_one_and_update(
            query, {"$set": fields}, return_document=ReturnDocument.AFTER, projection={"_id": 0}
        )

    async def delete(self, coll, id):
        res = await self.db[coll].delete_one({"id": id})
        return res.deleted_count > 0

    async def ping(self):
        await self.client.admin.command("ping")
        return True

    async def close(self):
        self.client.close()


def make_db():
    if settings.MONGODB_URI:
        return MongoDB(settings.MONGODB_URI, settings.MONGODB_DB)
    return MemoryDB()
