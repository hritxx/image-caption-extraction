from dotenv import load_dotenv
import os
import logging

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv("API_KEY", "your-default-api-key")

# Storage Configuration
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "duckdb")  # Options: duckdb, sqlite, postgres
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/store.db")
POSTGRES_URI = os.getenv("POSTGRES_URI", "postgresql://user:password@localhost:5432/papers")

# Data Source Configuration
DATA_SOURCE = os.getenv("DATA_SOURCE", "pmc")  # Options: pmc, pubmed, etc.

#api configuration
API_KEY = os.getenv("API_KEY", "default-api-key")
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "paper_extractor.log")

# Set up logging based on configuration
logging_level = getattr(logging, LOG_LEVEL.upper())
logging.basicConfig(
    level=logging_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_FILE if LOG_FILE != "stdout" else None
)

# Batch processing configuration
WATCH_FOLDER = os.getenv("WATCH_FOLDER", "watch")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))



ENABLE_ENTITY_EXTRACTION = os.getenv("ENABLE_ENTITY_EXTRACTION", "true").lower() == "true"
