from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from typing import List, Optional
import os
import logging
from config import DUCKDB_PATH
import duckdb
from contextlib import asynccontextmanager
from storage import init_db
from fastapi.responses import StreamingResponse
import io
import csv

from extractor import process_paper_id
from storage import get_paper_data, get_all_papers
from config import API_KEY

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

app = FastAPI(title="Paper Extractor API",
              description="Extract and store data from PMC papers")

def verify_api_key(key: str = Depends(api_key_header)):
    if key != API_KEY:
        logger.warning(f"Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Invalid API key"
        )
    return key

class ExtractRequest(BaseModel):
    paper_ids: List[str]

class ExtractResponse(BaseModel):
    id: str
    status: str
    error: Optional[str] = None
    note: Optional[str] = None
    

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ✅ Called at startup
    init_db()
    yield
    # ⬇️ You can add cleanup code here (on shutdown), if needed

app = FastAPI(
    title="Paper Extractor API",
    description="Extract and store data from PMC papers",
    lifespan=lifespan  # ✅ Use the new lifespan handler
)

@app.post("/extract", response_model=List[ExtractResponse])
def extract_papers(req: ExtractRequest, _: str = Depends(verify_api_key)):
    """Extract and store data for the provided paper IDs"""
    from extractor import get_pmcid_from_database
    
    results = []
    for pid in req.paper_ids:
        try:
            # Check if this is a PMCID that's already in our database
            if pid.upper().startswith("PMC"):
                conn = duckdb.connect(DUCKDB_PATH)
                paper_result = conn.execute(
                    "SELECT pmcid FROM publications WHERE pmcid = ?", 
                    [pid.upper()]
                ).fetchone()
                conn.close()
                
                if paper_result:
                    logger.info(f"Paper {pid} already exists in database, skipping extraction")
                    results.append({"id": pid, "status": "success", "note": "Retrieved from database"})
                    continue
            
            # If this is a PMID, check if we have a corresponding PMCID already in the database
            elif not pid.upper().startswith("PMC"):
                # First check if the PMID has a known PMCID
                pmcid = get_pmcid_from_database(pid)
                if pmcid:
                    # Now check if that PMCID is already in our publications table
                    conn = duckdb.connect(DUCKDB_PATH)
                    paper_result = conn.execute(
                        "SELECT pmcid FROM publications WHERE pmcid = ?", 
                        [pmcid.upper()]
                    ).fetchone()
                    conn.close()
                    
                    if paper_result:
                        logger.info(f"Paper with PMID {pid} (PMCID: {pmcid}) already exists in database, skipping extraction")
                        results.append({"id": pid, "status": "success", "note": f"Retrieved from database as {pmcid}"})
                        continue
            
            # If we get here, we need to extract the paper
            process_paper_id(pid)
            results.append({"id": pid, "status": "success"})
        except Exception as e:
            logger.error(f"Error processing paper {pid}: {e}")
            results.append({"id": pid, "status": "failed", "error": str(e)})
    return results


@app.get("/papers/{paper_id}")
def get_paper(paper_id: str, _: str = Depends(verify_api_key)):
    """Get data for a specific paper by ID (PMCID or PMID)"""
    from extractor import get_pmcid_from_database
    
    # First try direct lookup (for PMCID)
    data = get_paper_data(paper_id)
    
    # If not found and this is a PMID, try to convert to PMCID first
    if not data and not paper_id.upper().startswith("PMC"):
        logger.info(f"Paper {paper_id} not found directly, trying PMID to PMCID conversion...")
        pmcid = get_pmcid_from_database(paper_id)
        
        if pmcid:
            logger.info(f"Found PMCID {pmcid} for PMID {paper_id}, retrieving data...")
            data = get_paper_data(pmcid)
            
            # If data found, add the original PMID to the response
            if data:
                data["pmid"] = paper_id
    
    if not data:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    return data


@app.get("/db-stats")
def db_statistics(_: str = Depends(verify_api_key)):
    """Get database statistics without returning all the data"""
    try:
        conn = duckdb.connect(DUCKDB_PATH)
        count = conn.execute("SELECT COUNT(*) FROM publications").fetchone()[0]
        return {
            "total_papers": count,
            "database_path": DUCKDB_PATH
        }
    except Exception as e:
        logger.error(f"Error getting database statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    finally:
        if 'conn' in locals():
            conn.close()
            

@app.get("/papers/{paper_id}/csv")
def get_paper_csv(paper_id: str, _: str = Depends(verify_api_key)):
    """Get data for a specific paper in CSV format (PMCID or PMID)"""
    from extractor import get_pmcid_from_database
    
    # First try direct lookup (for PMCID)
    data = get_paper_data(paper_id)
    original_pmid = None
    
    # If not found and this is a PMID, try to convert to PMCID first
    if not data and not paper_id.upper().startswith("PMC"):
        logger.info(f"Paper {paper_id} not found directly, trying PMID to PMCID conversion...")
        pmcid = get_pmcid_from_database(paper_id)
        
        if pmcid:
            logger.info(f"Found PMCID {pmcid} for PMID {paper_id}, retrieving data...")
            data = get_paper_data(pmcid)
            if data:
                original_pmid = paper_id
    
    if not data:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # Create a CSV string
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header (add PMID if applicable)
    if original_pmid or not paper_id.upper().startswith("PMC"):
        writer.writerow(["pmid", "pmcid", "title", "abstract", "figure_caption", "figure_url"])
    else:
        writer.writerow(["pmcid", "title", "abstract", "figure_caption", "figure_url"])
    
    # Use the original PMID if we had to convert
    pmid_to_use = original_pmid if original_pmid else paper_id if not paper_id.upper().startswith("PMC") else None
    
    # Write data rows - one row per figure
    for figure in data["figures"]:
        if pmid_to_use:
            writer.writerow([
                pmid_to_use,
                data["pmcid"],
                data["title"],
                data["abstract"],
                figure["caption"],
                figure.get("url", "")
            ])
        else:
            writer.writerow([
                data["pmcid"],
                data["title"],
                data["abstract"],
                figure["caption"],
                figure.get("url", "")
            ])
    
    # If no figures, write a single row
    if not data["figures"]:
        if pmid_to_use:
            writer.writerow([pmid_to_use, data["pmcid"], data["title"], data["abstract"], "", ""])
        else:
            writer.writerow([data["pmcid"], data["title"], data["abstract"], "", ""])
    
    # Create response
    response = StreamingResponse(
        iter([output.getvalue()]), 
        media_type="text/csv"
    )
    response.headers["Content-Disposition"] = f"attachment; filename={paper_id}.csv"
    
    return response

@app.get("/papers/csv")
def get_all_papers_csv(_: str = Depends(verify_api_key)):
    """Get all papers in CSV format"""
    papers = get_all_papers()
    
    # Create a CSV string
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(["pmcid", "title", "abstract", "figure_caption", "figure_url"])
    
    # Write data rows
    for paper in papers:
        for figure in paper["figures"]:
            writer.writerow([
                paper["pmcid"],
                paper["title"],
                paper["abstract"],
                figure["caption"],
                figure.get("url", "")
            ])
        
        # If no figures, write a single row
        if not paper["figures"]:
            writer.writerow([paper["pmcid"], paper["title"], paper["abstract"], "", ""])
    
    # Create response
    response = StreamingResponse(
        iter([output.getvalue()]), 
        media_type="text/csv"
    )
    response.headers["Content-Disposition"] = "attachment; filename=all_papers.csv"
    
    return response