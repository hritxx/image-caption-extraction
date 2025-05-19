# Deployment Guide for Paper Extractor

This guide explains how to deploy and configure the Paper Extractor system.

## Prerequisites

- Docker and Docker Compose installed
- Git (to clone the repository)

## Configuration Options

The system is configured through environment variables, which can be set in a `.env` file:

| Variable     | Description                              | Default                                            |
| ------------ | ---------------------------------------- | -------------------------------------------------- |
| API_KEY      | API key for authentication               | "your-default-api-key"                             |
| STORAGE_TYPE | Storage backend type                     | "duckdb"                                           |
| DUCKDB_PATH  | Path to DuckDB database                  | "data/store.db"                                    |
| POSTGRES_URI | PostgreSQL connection URI                | "postgresql://user:password@localhost:5432/papers" |
| DATA_SOURCE  | Source of paper data                     | "pmc"                                              |
| LOG_LEVEL    | Logging level                            | "INFO"                                             |
| LOG_FILE     | Log file path (use "stdout" for console) | "paper_extractor.log"                              |
| WATCH_FOLDER | Folder to watch for batch processing     | "watch"                                            |
| BATCH_SIZE   | Number of papers to process in a batch   | 10                                                 |

## Deployment Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/paper-extractor.git
   cd paper-extractor
   ```
