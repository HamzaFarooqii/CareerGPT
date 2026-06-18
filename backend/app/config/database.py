# ============================================================
# Database — MongoDB Connection Manager
# ============================================================
# This module handles connecting to and disconnecting from MongoDB.
#
# CONCEPT: Connection Lifecycle
# ─────────────────────────────
# A database connection is like a phone call:
#   1. You DIAL (connect) when the app starts
#   2. You TALK (read/write data) while the app runs
#   3. You HANG UP (disconnect) when the app stops
#
# If you connect on every request, that's like dialing a new
# phone call for every sentence — slow and wasteful.
# Instead, we connect ONCE at startup and reuse that connection.
#
# CONCEPT: Async (motor vs pymongo)
# ──────────────────────────────────
# pymongo = synchronous (blocking)
#   → While waiting for MongoDB, your server does NOTHING
#   → Like waiting in line at a restaurant — you just stand there
#
# motor = asynchronous (non-blocking)
#   → While waiting for MongoDB, your server handles OTHER requests
#   → Like taking a number at a deli — you go do other things
#
# For a web server, async is way better because you might have
# 10 users hitting your API at the same time.
# ============================================================

from motor.motor_asyncio import AsyncIOMotorClient

from .settings import settings


class Database:
    """
    MongoDB connection manager.
    
    Usage:
        from app.config.database import db
        
        # Get a collection (like a table in SQL)
        collection = db.get_collection("resumes")
        
        # Insert a document (like a row in SQL)
        await collection.insert_one({"name": "Hamza", "skills": ["Python"]})
        
        # Find documents
        resume = await collection.find_one({"name": "Hamza"})
    """

    def __init__(self):
        # These start as None because we haven't connected yet.
        # They get set in connect_db().
        self.client: AsyncIOMotorClient | None = None
        self.database = None

    async def connect_db(self):
        """
        Open the connection to MongoDB.
        Called once when the app starts (see main.py lifespan).
        
        AsyncIOMotorClient creates a CONNECTION POOL — a set of
        reusable connections. When your code needs MongoDB, it
        grabs a connection from the pool, uses it, and returns it.
        This is way faster than connecting/disconnecting every time.
        """
        print(f"📦 Connecting to MongoDB at {settings.MONGODB_URL}...")
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.database = self.client[settings.DATABASE_NAME]

        # Verify the connection works by pinging the server.
        # If MongoDB isn't running, this will throw an error
        # immediately — fail fast!
        try:
            await self.client.admin.command("ping")
            print(f"✅ Connected to MongoDB database: {settings.DATABASE_NAME}")
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            raise

    async def close_db(self):
        """
        Close the connection when the app shuts down.
        This frees up resources (like hanging up the phone).
        """
        if self.client:
            self.client.close()
            print("🔌 MongoDB connection closed")

    def get_collection(self, name: str):
        """
        Get a MongoDB collection by name.
        
        CONCEPT: Collections vs Tables
        ──────────────────────────────
        In SQL (like your Cafe Management project):
            - Database → Tables → Rows → Columns
            - Schema is FIXED — every row has the same columns
        
        In MongoDB:
            - Database → Collections → Documents → Fields
            - Schema is FLEXIBLE — documents can have different fields
            
        Why MongoDB for this project?
        Job listings from different websites have different fields.
        Rozee.pk might have "salary_range" but Indeed might not.
        MongoDB handles this naturally — no schema migrations needed.
        """
        if self.database is None:
            raise RuntimeError("Database not connected. Call connect_db() first.")
        return self.database[name]


# Single instance shared across the app
db = Database()
