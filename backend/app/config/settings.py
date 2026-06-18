# ============================================================
# Settings — Multi-Provider AI Configuration
# ============================================================

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """
    Application settings with multi-provider AI support.
    Set AI_PROVIDER in .env to: "groq" | "gemini" | "openrouter"
    """

    def __init__(self):
        # --- Database ---
        self.MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        self.DATABASE_NAME: str = os.getenv("DATABASE_NAME", "jobmatchr")

        # --- Server ---
        self.HOST: str = os.getenv("HOST", "0.0.0.0")
        self.PORT: int = int(os.getenv("PORT", "8000"))
        self.ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

        # ── AI Provider Selection ────────────────────────────
        self.AI_PROVIDER: str = os.getenv("AI_PROVIDER", "groq")  # groq | gemini | openrouter

        # --- Groq (Recommended — 14,400 req/day FREE) ---
        self.GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
        self.GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

        # --- Google Gemini (1,500 req/day FREE) ---
        self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
        self.LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.0-flash")

        # --- OpenRouter (free models available) ---
        self.OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
        self.OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-70b-instruct:free")

        # ── Embedding Provider ───────────────────────────────
        # "local"  = Sentence Transformers (FREE, no API, runs on your machine)
        # "gemini" = Google embedding API (1500/day free)
        # "cohere" = Cohere (1000/month free)
        self.EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "local")
        self.EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

        # Cohere (fallback embedding)
        self.COHERE_API_KEY: str = os.getenv("COHERE_API_KEY", "")

        # --- Upload ---
        self.MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))
        self.UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
        Path(self.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

    def validate(self):
        """Validate that at least one AI provider is configured."""
        has_groq = bool(self.GROQ_API_KEY and self.GROQ_API_KEY != "your_groq_api_key_here")
        has_gemini = bool(self.GEMINI_API_KEY and "AIza" in self.GEMINI_API_KEY)
        has_openrouter = bool(self.OPENROUTER_API_KEY and self.OPENROUTER_API_KEY != "your_openrouter_key_here")

        if not any([has_groq, has_gemini, has_openrouter]):
            raise ValueError(
                "❌ No AI API key configured!\n"
                "   Option 1 (RECOMMENDED): Get free Groq key at https://console.groq.com\n"
                "   Option 2: Get free Gemini key at https://aistudio.google.com/apikey\n"
                "   Then add it to backend/.env"
            )

        # Auto-select provider based on available keys
        if self.AI_PROVIDER == "groq" and not has_groq:
            if has_gemini:
                print("⚠️  Groq key missing, falling back to Gemini")
                self.AI_PROVIDER = "gemini"
            elif has_openrouter:
                print("⚠️  Groq key missing, falling back to OpenRouter")
                self.AI_PROVIDER = "openrouter"

        print(f"✅ AI Provider: {self.AI_PROVIDER.upper()} | Embedding: {self.EMBEDDING_PROVIDER}")


settings = Settings()
