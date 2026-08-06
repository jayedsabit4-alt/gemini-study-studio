import os
from pathlib import Path

# Base Project Directory
BASE_DIR = Path(__file__).resolve().parent

# Storage Paths
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_FOLDER = STORAGE_DIR / "uploads"
EXPORT_FOLDER = STORAGE_DIR / "exports"
BACKUP_FOLDER = STORAGE_DIR / "backups"
DATABASE_PATH = STORAGE_DIR / "study.db"

for folder in [STORAGE_DIR, UPLOAD_FOLDER, EXPORT_FOLDER, BACKUP_FOLDER]:
    folder.mkdir(parents=True, exist_ok=True)

# OpenRouter & LLM Settings
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openrouter/free"
FALLBACK_MODELS = [
    "openrouter/free",
    "google/gemma-2-9b-it:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "deepseek/deepseek-r1:free",
]
DEFAULT_TIMEOUT = 45.0
DEFAULT_TEMPERATURE = 0.7
MAX_RETRIES = 2

# Document Parsing & Table Limits
MAX_TABLE_ROWS = 1000

# RAG & Speed Optimization Settings
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_CHUNK_SIZE = 1000       # Larger chunk size = 50% fewer embeddings needed
DEFAULT_CHUNK_OVERLAP = 100
MAX_DOCUMENT_CHUNKS = 200       # Caps giant files to 200 chunks for instant indexing
DEFAULT_TOP_K = 4
DEFAULT_SCORE_THRESHOLD = 0.25
MAX_RAG_CONTEXT_CHARS = 12000

CHUNK_SIZE = DEFAULT_CHUNK_SIZE
CHUNK_OVERLAP = DEFAULT_CHUNK_OVERLAP
