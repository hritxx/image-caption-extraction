import duckdb
import json
import logging
import os
from config import DUCKDB_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db(db_path=DUCKDB_PATH):
    """
    Initializes the DuckDB database and creates the publications table if it doesn't exist.
    """
    # Ensure the directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = duckdb.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS publications (
            pmcid TEXT PRIMARY KEY,
            title TEXT,
            abstract TEXT,
            figures_json TEXT
        )
    """)
    logger.info(f"Database initialized at {db_path}")
    return conn

def insert_paper(conn, data):
    """
    Inserts a paper's data into the publications table.
    """
    try:
        conn.execute("""
            INSERT OR REPLACE INTO publications (pmcid, title, abstract, figures_json)
            VALUES (?, ?, ?, ?)
        """, (data["pmcid"], data["title"], data["abstract"], json.dumps(data["figures"])))
        logger.info(f"Paper {data['pmcid']} inserted into the database.")
    except Exception as e:
        logger.error(f"Error inserting paper {data['pmcid']}: {e}")

def get_paper_data(paper_id):
    """
    Retrieves a specific paper's data from the database.
    
    Args:
        paper_id (str): The PMC ID of the paper to retrieve
        
    Returns:
        dict: The paper data or None if not found
    """
    try:
        # Ensure the PMC prefix is present
        if not paper_id.startswith("PMC"):
            paper_id = f"PMC{paper_id}"
            
        conn = duckdb.connect(DUCKDB_PATH)
        result = conn.execute(
            "SELECT pmcid, title, abstract, figures_json FROM publications WHERE pmcid = ?",
            [paper_id]
        ).fetchone()
        
        if not result:
            logger.info(f"No paper found with ID: {paper_id}")
            return None
            
        pmcid, title, abstract, figures_json = result
        
        # Parse the figures JSON
        figures = json.loads(figures_json) if figures_json else []
        
        return {
            "pmcid": pmcid,
            "title": title,
            "abstract": abstract,
            "figures": figures
        }
    except Exception as e:
        logger.error(f"Error retrieving paper {paper_id}: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def get_all_papers():
    """
    Retrieves all papers from the database.
    
    Returns:
        list: A list of paper dictionaries
    """
    try:
        conn = duckdb.connect(DUCKDB_PATH)
        results = conn.execute(
            "SELECT pmcid, title, abstract, figures_json FROM publications"
        ).fetchall()
        
        papers = []
        for result in results:
            pmcid, title, abstract, figures_json = result
            figures = json.loads(figures_json) if figures_json else []
            papers.append({
                "pmcid": pmcid,
                "title": title,
                "abstract": abstract,
                "figures": figures
            })
            
        return papers
    except Exception as e:
        logger.error(f"Error retrieving all papers: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()