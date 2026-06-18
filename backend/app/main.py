# ============================================================
# Main — FastAPI Application Entry Point
# ============================================================
# This is the file that ties everything together.
# When you run `uvicorn app.main:app`, Python loads THIS file
# and starts the FastAPI server.
#
# CONCEPT: Application Lifecycle
# ──────────────────────────────
# A web server has a lifecycle:
#   1. STARTUP: Connect to databases, load models, warm caches
#   2. RUNNING: Handle requests (this is where the app spends most time)
#   3. SHUTDOWN: Close connections, save state, clean up
#
# FastAPI's "lifespan" context manager handles steps 1 and 3.
# The code before `yield` runs at startup.
# The code after `yield` runs at shutdown.
# ============================================================

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.database import db
from app.config.settings import settings
from app.routes import resume, jobs, matches, auth, coach, apply


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager.
    
    CONCEPT: Context Manager (the `async with` pattern)
    ────────────────────────────────────────────────────
    A context manager ensures cleanup happens even if something crashes.
    
    Think of it like a try/finally:
      try:
          connect_to_database()   ← startup
          yield                   ← app runs here
      finally:
          close_database()        ← shutdown (always runs)
    
    The `yield` keyword pauses this function. The app runs while
    it's paused. When the app stops, execution continues after yield.
    """
    # ── STARTUP ───────────────────────────────────────────
    print("=" * 50)
    print("🚀 CareerGPT is starting up...")
    print("=" * 50)

    # Validate settings (fail fast if config is wrong)
    settings.validate()
    print("✅ Settings validated")

    # Connect to MongoDB
    await db.connect_db()

    print(f"🌐 Server running at http://{settings.HOST}:{settings.PORT}")
    print(f"📖 API docs at http://localhost:{settings.PORT}/docs")
    print("=" * 50)

    # yield = "startup is done, start handling requests"
    yield

    # ── SHUTDOWN ──────────────────────────────────────────
    print("\n🛑 Shutting down...")
    await db.close_db()
    print("👋 Goodbye!")


# ── Create the FastAPI app ────────────────────────────────
#
# CONCEPT: What is FastAPI?
# ─────────────────────────
# FastAPI is a web framework — it handles the boring parts:
#   - Listening for HTTP requests
#   - Routing URLs to the right function
#   - Serializing/deserializing JSON
#   - Validating input data
#   - Generating API documentation
#
# You just write the business logic (what should happen
# when someone uploads a resume), and FastAPI handles the rest.

app = FastAPI(
    title="CareerGPT API",
    description=(
        "CareerGPT — AI-Powered Career Platform. "
        "Job matching, career coaching, resume optimization, and apply automation "
        "powered by Groq LLM + ChromaDB vector search."
    ),
    version="2.0.0",
    lifespan=lifespan,
)


# ── CORS Middleware ───────────────────────────────────────
#
# CONCEPT: CORS (Cross-Origin Resource Sharing)
# ──────────────────────────────────────────────
# By default, a web browser blocks requests from one domain
# to another. This is a security feature.
#
# Problem: Your React frontend runs on localhost:5173
#          Your FastAPI backend runs on localhost:8000
#          → The browser blocks the frontend from calling the backend!
#
# Solution: CORS middleware tells the browser "it's okay,
# localhost:5173 is allowed to call me."
#
# In production, you'd replace "*" with your actual domain.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Allow all origins (dev only)
    allow_credentials=True,
    allow_methods=["*"],        # Allow all HTTP methods
    allow_headers=["*"],        # Allow all headers
)


# ── Include Routers ───────────────────────────────────────
# Each router handles a group of related endpoints.
# This keeps code organized — resume logic in resume.py,
# job logic in jobs.py, etc.

app.include_router(resume.router)
app.include_router(jobs.router)
app.include_router(matches.router)
app.include_router(auth.router)
app.include_router(coach.router)
app.include_router(apply.router)


# ── Root endpoint ─────────────────────────────────────────
# A simple health check — "is the server running?"

@app.get("/")
async def root():
    """API root — basic info and health check."""
    return {
        "app": "CareerGPT",
        "version": "2.0.0",
        "status": "running",
        "description": "AI-Powered Career Platform — Job Matching, Career Coach, Apply Agent",
        "docs": f"http://localhost:{settings.PORT}/docs",
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    CONCEPT: Health Checks
    ──────────────────────
    In production, load balancers and monitoring tools ping
    this endpoint to verify the server is alive. If it returns
    an error, they can restart the server or alert the team.
    
    We also check database connectivity — a running server with
    a dead database is useless.
    """
    try:
        # Ping MongoDB to verify it's responsive
        await db.client.admin.command("ping")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "environment": settings.ENVIRONMENT,
    }


# ── Run with uvicorn when executed directly ───────────────
# This lets you do: python -m app.main
# But the standard way is: uvicorn app.main:app --reload

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,  # Auto-restart when code changes (dev only)
    )
