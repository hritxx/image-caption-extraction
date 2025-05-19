# Paper Extractor

A Python-based system for extracting and analyzing scientific paper data from PMC articles. This application helps researchers extract structured data from medical and scientific papers, including title, abstract, figures, and entity annotations.

## 🌟 Features

- **Paper Data Extraction**: Fetch title, abstract, and figures from PMC articles using the BioC-PMC API
- **Entity Recognition**: Annotate text with biomedical entities (genes, diseases, chemicals, etc.) using PubTator API
- **Data Storage**: Efficiently store extracted data in a DuckDB database
- **Easy Access**: RESTful API for programmatic access to extracted paper data
- **Export Options**: Download paper data in various formats (JSON, CSV)
- **Batch Processing**: Process multiple papers via a file watching mechanism
- **Containerized Deployment**: Dockerized for easy deployment

## 🧑‍💻 User Features

As a **User**:

- Submit a list of paper IDs (PMC or PMID) for data extraction
- Query extracted data using a simple API, protected by an API key
- Retrieve data in JSON or CSV formats
- Upload paper ID lists via API or command-line interface
- Access figure captions, titles, abstracts, and entity annotations

## 👨‍💼 Admin Features

As an **Admin**:

- Configure where data is stored (default: local DuckDB)
- Set and update API keys
- Choose which data source to use (PMC by default, with room for expansion)
- Configure logging level (info, debug)
- Add new data sources without rewriting the system
- Control batch processing parameters

## 🛠️ Ops Features

As an **Ops Person**:

- Deploy the system via Docker and Docker Compose
- Run ingestion jobs in batch mode through:
  - Processing a file of IDs
  - Handling an uploaded list
  - Monitoring a watched folder for new files
- Monitor logs and ingestion summaries
- Verify the system exits cleanly with clear success/failure status
- Check system health via dedicated endpoints

## 📦 Installation

### Prerequisites

- Python 3.9+
- pip
- Git

### Option 1: Local Installation

1. Clone the repository:

```bash
git clone https://github.com/hritxx/image-caption-extraction.git
cd image-caption-extraction
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables:

```bash
cp .env.example .env
# Edit .env with your preferred settings
```

4. Initialize the database:

```bash
python init_db.py
```

### Option 2: Docker Installation

1. Clone the repository:

```bash
git clone https://github.com/hritxx/image-caption-extraction.git
cd image-caption-extraction
```

2. Configure environment variables in `.env`

3. Build and start the services:

```bash
docker-compose up -d
```

## 🚀 Usage

### API Usage

The application provides a RESTful API with the following endpoints:

- **POST /extract** - Extract data from specified papers
- **GET /papers/{paper_id}** - Get data for a specific paper
- **GET /papers** - List all stored papers
- **GET /papers/{paper_id}/csv** - Get paper data in CSV format
- **GET /papers/csv** - Get all papers in CSV format
- **GET /health** - Health check endpoint
- **GET /db-stats** - Get database statistics

Example API request:

```bash
curl -X POST "http://localhost:8000/extract" \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"paper_ids": ["PMC7964769", "PMC7877219"]}'
```

### Command Line Interface

The project includes several CLI tools for various operations:

#### Main CLI

Process papers and interact with the database:

```bash
# Process papers from a file
python main_cli.py --file paper_ids.txt

# Get data for a specific paper
python main_cli.py --get PMC7964769

# Test fetching a specific paper directly
python main_cli.py --test PMC7964769

# List all papers in the database
python main_cli.py --list

# View raw database contents
python main_cli.py --db
```

#### Admin CLI

Configure the application:

```bash
# Show current configuration
python admin_cli.py config show

# Update configuration
python admin_cli.py config set API_KEY "new-api-key"
```

### Batch Processing

Place text files containing paper IDs (one per line) in the `watch` folder to process them automatically:

```bash
echo "PMC7964769" > watch/batch1.txt
```

The system will process the papers and create a `.processed` file with results.

## 🌐 Deployed API Documentation

The API is deployed and accessible at: http://20.193.148.209:9000

You can interact with the deployed API using the following endpoints:

1. **Health Check**: Verify the API is running
2. **Get Database Statistics**: Retrieve information about the stored papers
3. **Retrieve a Specific Paper**: Get data for a paper by its ID
4. **Download Data in CSV Format**: Export paper data as CSV

### Python Example

Here's how to use the deployed API in Python:

```python
import requests

# API base URL
API_URL = "http://20.193.148.209:9000"
API_KEY = "new-secure-key"  # Test API key

# Headers for authentication
headers = {
    "X-API-Key": API_KEY
}

# Check API health
health_response = requests.get(f"{API_URL}/health")
print(f"API Health: {health_response.json()}")

# Get database statistics
stats_response = requests.get(f"{API_URL}/db-stats", headers=headers)
print(f"Database Stats: {stats_response.json()}")

# Get a specific paper
paper_id = "PMC7964769"
paper_response = requests.get(f"{API_URL}/papers/{paper_id}", headers=headers)
paper_data = paper_response.json()
print(f"Paper Title: {paper_data['title']}")

# Download a paper's data in CSV format
csv_response = requests.get(f"{API_URL}/papers/{paper_id}/csv", headers=headers)
with open(f"{paper_id}.csv", "wb") as f:
    f.write(csv_response.content)
print(f"CSV saved to {paper_id}.csv")
```

### Important Notes

- The API requires an API key for authentication (provided as X-API-Key header)
- The current API key for testing is: `new-secure-key`
- For production use, please request a dedicated API key
- There are rate limits of 100 requests per hour
- The server performs daily maintenance between 3-4 AM UTC

## 🏗️ Project Structure

```
paper-extractor/
├── api.py              # FastAPI web application
├── batch_processor.py  # File watcher for batch processing
├── config.py           # Configuration and environment variables
├── docker-compose.yml  # Docker Compose configuration
├── Dockerfile          # Docker build instructions
├── extractor.py        # Paper data extraction logic
├── init_db.py          # Database initialization script
├── main_cli.py         # Command-line interface
├── admin_cli.py        # Admin configuration CLI
├── storage.py          # Database operations
├── requirements.txt    # Python dependencies
├── data/               # Database storage (created at runtime)
├── logs/               # Log files (created at runtime)
└── watch/              # Folder for batch processing files
```

## 🔧 Configuration

Configure the application through environment variables in an `.env` file:

| Variable                 | Description                       | Default                |
| ------------------------ | --------------------------------- | ---------------------- |
| API_KEY                  | API key for authentication        | "your-default-api-key" |
| STORAGE_TYPE             | Storage backend type              | "duckdb"               |
| DUCKDB_PATH              | Path to DuckDB database           | "data/store.db"        |
| LOG_LEVEL                | Logging level                     | "INFO"                 |
| LOG_FILE                 | Log file path                     | "paper_extractor.log"  |
| WATCH_FOLDER             | Folder to watch for batch files   | "watch"                |
| BATCH_SIZE               | Papers to process in one batch    | 10                     |
| ENABLE_ENTITY_EXTRACTION | Enable PubTator entity extraction | "true"                 |

## 🔍 Data Extraction Process

1. The system fetches paper data from the BioC-PMC API using the PMC ID
2. It extracts the paper's title, abstract, and figures
3. For each figure caption, it can optionally extract biomedical entities using the PubTator API
4. All data is stored in a DuckDB database for efficient retrieval
5. The data can be accessed through the API or exported in various formats

## 🧪 Example

Extract data from a PMC article and retrieve it in JSON format:

```python
import requests

# Extract a paper
requests.post(
    "http://localhost:9000/extract",
    headers={"X-API-Key": "your-api-key"},
    json={"paper_ids": ["PMC7964769"]}
)

# Retrieve the paper
paper = requests.get(
    "http://localhost:9000/papers/PMC7964769",
    headers={"X-API-Key": "your-api-key"}
).json()

print(f"Title: {paper['title']}")
print(f"Abstract: {paper['abstract'][:100]}...")
print(f"Number of figures: {len(paper['figures'])}")
```

## 🔄 Role-Based Usage Scenarios

### For Users

As a researcher, you can:

1. Submit a list of paper IDs for extraction via the API or CLI
2. Query the extracted data to analyze figure captions and metadata
3. Export the data in JSON or CSV format for further analysis
4. Access entity annotations for biomedical concepts in figure captions

### For Admins

As a system administrator, you can:

1. Configure the storage backend based on your needs
2. Set up API keys for secure access
3. Configure logging to troubleshoot issues
4. Enable or disable features like entity extraction
5. Extend the system with new data sources when needed

### For Ops

As an operations engineer, you can:

1. Deploy the system using Docker Compose
2. Set up batch processing jobs via the watched folder
3. Monitor system performance and logs
4. Verify successful processing with status files
5. Check system health via the health endpoint

## 📝 License

[MIT License](LICENSE)

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

# image-caption-extraction
