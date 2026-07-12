import os

from dotenv import load_dotenv

# Loads variables from a local .env file for local (non-Docker) testing.
# Does NOT override variables already set in the environment (e.g. by
# docker-compose's `environment:` block), so this is safe in both contexts.
load_dotenv()

CONNECTION_STRING = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://novatech:novatech@localhost:5432/novatech"
)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "gpt-4o-mini")

# Text chunking parameters (characters)
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "100"))

# PGVector collection names. Text uses a plain collection; tables use a
# MultiVectorRetriever (embedded summary -> full table via ID_KEY lookup).
TEXT_COLLECTION = "novatech_text_chunks"
TABLE_COLLECTION = "novatech_tables"
ID_KEY = "doc_id"
