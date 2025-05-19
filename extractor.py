import requests
import xml.etree.ElementTree as ET
import logging
import json
import time
from storage import init_db, insert_paper
from config import DUCKDB_PATH
from config import ENABLE_ENTITY_EXTRACTION
import duckdb
from config import NCBI_API_KEY



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_entities_from_bern(caption: str, max_retries=3):
    if not ENABLE_ENTITY_EXTRACTION:
        logger.debug("Entity extraction disabled")
        return []

    if len(caption) < 20:
        logger.debug("Caption too short")
        return []

    url = "http://bern2.korea.ac.kr/plain"

    payload = {"text": caption}
    headers = {"Content-Type": "application/json"}

    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            entities = []
            for ann in data.get("annotations", []):
                # Use defensive coding to avoid index errors
                entity = {
                    "text": ann.get("mention", ""),
                    "type": ann.get("obj", "unknown"),
                    "identifier": None,  # Initialize with default value
                    "start": ann.get("span", {}).get("begin", 0),
                    "end": ann.get("span", {}).get("end", 0)
                }
                
                # Safely get identifier from id list if it exists
                id_list = ann.get("id", [])
                if id_list and len(id_list) > 0:
                    entity["identifier"] = id_list[0]
                
                entities.append(entity)

            logger.info(f"Extracted {len(entities)} entities")
            return entities

        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            # Add a delay between retries
            time.sleep(2 * (attempt + 1))  # Progressive backoff

    logger.error("All attempts failed")
    return []


def check_pmc_id_exists(pmc_id: str) -> bool:
    """Check if a PMC ID exists by making a HEAD request to the NCBI server.
    
    Args:
        pmc_id (str): The PMC ID to check, with or without the 'PMC' prefix
        
    Returns:
        bool: True if the PMC ID exists, False otherwise
    """
    import requests
    
    # Ensure PMC ID has the correct format
    if not pmc_id.upper().startswith("PMC"):
        pmc_id = f"PMC{pmc_id}"
        
    base_url = f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/{pmc_id}/unicode"
    url = f"{base_url}?api_key={NCBI_API_KEY}" if NCBI_API_KEY else base_url
    
    try:
        # Use a HEAD request to check if the resource exists without downloading it
        response = requests.head(url, timeout=10)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def fetch_bioc_paper(pmc_id: str, format: str = "xml", encoding: str = "unicode"):
    """
    Fetches the BioC-formatted data for a given PMC ID and extracts the title, abstract, and figures.
    
    Args:
        pmc_id (str): The PMC ID (can be with or without the 'PMC' prefix)
        format (str): Either "xml" or "json"
        encoding (str): Either "unicode" or "ascii"
    """
    # Ensure PMC ID has the correct format
    if not pmc_id.startswith("PMC"):
        pmc_id = f"PMC{pmc_id}"
    
    base_url = f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_{format}/{pmc_id}/{encoding}"
    
    # Add API key to URL if available
    url = f"{base_url}?api_key={NCBI_API_KEY}" if NCBI_API_KEY else base_url
    
    try:
        logger.info(f"Fetching {url.split('?')[0]}")  # Log URL without API key
        response = requests.get(url)
        response.raise_for_status()
        
        # Save response for debugging
        with open(f"{pmc_id}_response.xml", "w", encoding="utf-8") as f:
            f.write(response.text)
        logger.info(f"Response saved to {pmc_id}_response.xml")
        
        if format == "json":
            data = response.json()
            # Extract information from JSON structure
            logger.warning("JSON parsing not fully implemented yet")
            return None
        else:  # XML format
            root = ET.fromstring(response.text)
            
            title = ""
            abstract = ""
            figures = []
            
            # Print root structure for debugging
            logger.info(f"XML root tag: {root.tag}")
            for child in root:
                logger.info(f"Child tag: {child.tag}")
            
            # First, try to find document(s) in the collection
            documents = root.findall(".//document")
            logger.info(f"Found {len(documents)} documents in XML")
            
            for document in documents:
                # Extract title from article-title sections or passages
                title_elements = document.findall(".//passage/infon[@key='section_type'][.='TITLE']/..")
                title_elements += document.findall(".//passage/infon[@key='type'][.='title']/..")
                
                if title_elements:
                    for title_elem in title_elements:
                        text_elem = title_elem.find("text")
                        if text_elem is not None and text_elem.text:
                            title = text_elem.text
                            break
                
                # Extract abstract from abstract sections or passages
                abstract_elements = document.findall(".//passage/infon[@key='section_type'][.='ABSTRACT']/..")
                abstract_elements += document.findall(".//passage/infon[@key='type'][.='abstract']/..")
                
                for abstract_elem in abstract_elements:
                    text_elem = abstract_elem.find("text")
                    if text_elem is not None and text_elem.text:
                        if abstract:
                            abstract += " " + text_elem.text
                        else:
                            abstract = text_elem.text
                
                # Find figures
                figure_elements = document.findall(".//passage/infon[@key='section_type'][.='FIG']/..")
                figure_elements += document.findall(".//passage/infon[@key='section_type'][.='FIGURE']/..")
                figure_elements += document.findall(".//passage/infon[@key='type'][.='fig']/..")
                figure_elements += document.findall(".//passage/infon[@key='type'][.='figure-caption']/..")
                
                for fig_elem in figure_elements:
                    text_elem = fig_elem.find("text")
                    if text_elem is not None and text_elem.text:
                        figure_caption = text_elem.text
                        figure_url = None
                        
                        # Try to find figure URL in infon elements
                        for infon in fig_elem.findall("infon"):
                            if infon.get("key") in ["url", "file", "fig_url"]:
                                figure_url = infon.text
                        
                        entities = fetch_entities_from_bern(figure_caption)  # Changed function call
                        figures.append({
                            "caption": figure_caption,
                            "url": figure_url,
                            "entities": entities
                        })
                
                # If we found no title yet, look for article title at the document level
                if not title:
                    for infon in document.findall("infon"):
                        if infon.get("key") == "article-title":
                            title = infon.text
                            break
            
            # If still no title found, try to find the journal-title at a higher level
            if not title:
                for infon in root.findall(".//infon[@key='article-title']"):
                    title = infon.text
                    break
            
            # Log what we found for debugging
            logger.info(f"Extracted title length: {len(title)}")
            logger.info(f"Extracted abstract length: {len(abstract)}")
            logger.info(f"Number of figures found: {len(figures)}")
            
            # Only return if we found some data
            if title or abstract or figures:
                return {
                    "pmcid": pmc_id,
                    "title": title,
                    "abstract": abstract,
                    "figures": figures
                }
            else:
                logger.error(f"No content could be extracted from {pmc_id}")
                return None

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.error(f"PMC {pmc_id} not found or not in the Open Access subset")
        else:
            logger.error(f"HTTP error fetching PMC {pmc_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching PMC {pmc_id}: {e}")
        return None
    


    """
    Check if a PMC ID exists in the PMC database without downloading the full text
    
    Args:
        pmc_id (str): The PMC ID (with or without PMC prefix)
    
    Returns:
        bool: True if the PMC ID exists, False otherwise
    """
    # Ensure PMC ID has the correct format for the URL
    if not pmc_id.startswith("PMC"):
        formatted_id = f"PMC{pmc_id}"
    else:
        formatted_id = pmc_id
    
    # Use NCBI's efetch utility to just check if the ID exists
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pmc",
        "id": formatted_id,
        "retmode": "xml",
        "rettype": "docsum"
    }
    
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    
    try:
        logger.info(f"Checking if PMC ID exists: {formatted_id}")
        response = requests.get(base_url, params=params)
        
        # If we get a valid response without error content, the ID exists
        if response.status_code == 200 and "<ERROR>" not in response.text:
            return True
        else:
            # Log the error from NCBI if any
            if "<ERROR>" in response.text:
                import re
                error_match = re.search(r'<ERROR>(.*?)</ERROR>', response.text)
                if error_match:
                    logger.warning(f"NCBI Error for {formatted_id}: {error_match.group(1)}")
            return False
    
    except Exception as e:
        logger.error(f"Error checking PMC ID {formatted_id}: {str(e)}")
        return False

def get_pmcid_from_database(pmid: str) -> str:
    """
    Look up a PMCID for a given PMID using the local mapping database.
    
    Args:
        pmid (str): The PubMed ID to look up
    
    Returns:
        str: The corresponding PMCID if found, None otherwise
    """
    try:
        # Connect to the database
        conn = duckdb.connect(DUCKDB_PATH)
        
        # Check if the pmid_to_pmcid table exists
        tables = conn.execute("SHOW TABLES").fetchall()
        if not any(t[0] == 'pmid_to_pmcid' for t in tables):
            logger.warning("pmid_to_pmcid table does not exist in the database")
            return None
        
        # Query the mapping
        result = conn.execute(
            "SELECT pmcid FROM pmid_to_pmcid WHERE pmid = ?", 
            [pmid.strip()]
        ).fetchone()
        
        if result:
            pmcid = result[0]
            # Ensure PMC prefix
            if not pmcid.upper().startswith("PMC"):
                pmcid = f"PMC{pmcid}"
            logger.info(f"Found PMCID {pmcid} for PMID {pmid} in database")
            return pmcid
        else:
            logger.info(f"No PMCID found for PMID {pmid} in database")
            return None
        
    except Exception as e:
        logger.error(f"Error looking up PMCID for PMID {pmid}: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()


def process_paper_id(pmc_id: str):
    """Process a paper ID through the extraction pipeline and store it in the database.
    
    This function accepts either a PMC ID or PMID and processes it accordingly.
    """
    logger.info(f"Processing paper ID: {pmc_id}")
    
    # Step 1: Handle PMID to PMCID conversion if needed
    # If it's not already a PMCID, we need to convert it
    if not pmc_id.upper().startswith("PMC"):
        logger.info(f"{pmc_id} appears to be a PMID, attempting to convert to PMCID...")
        
        # First check database
        db_pmcid = get_pmcid_from_database(pmc_id)
        if db_pmcid:
            logger.info(f"Found PMCID {db_pmcid} for PMID {pmc_id} in local database")
            pmc_id = db_pmcid
        else:
            # Try API conversion
            from help import convert_pmid_to_pmcid
            api_pmcid = convert_pmid_to_pmcid(pmc_id)
            if api_pmcid:
                logger.info(f"Converted PMID {pmc_id} to PMCID {api_pmcid} via NCBI API")
                pmc_id = api_pmcid
            else:
                logger.error(f"Failed to convert PMID {pmc_id} to a PMCID")
                raise ValueError(f"Failed to fetch paper: PMID {pmc_id} has no corresponding PMCID")
    
    # Step 2: Ensure PMCID has PMC prefix
    if not pmc_id.upper().startswith("PMC"):
        pmc_id = f"PMC{pmc_id}"
    
    # Step 3: Fetch the paper data
    logger.info(f"Fetching article with PMCID: {pmc_id}")
    paper_data = fetch_bioc_paper(pmc_id)
    
    if not paper_data:
        logger.error(f"Failed to retrieve data for PMCID {pmc_id}")
        raise ValueError(f"Failed to fetch paper with ID: {pmc_id}")
    
    # Process entity extraction if enabled
    if ENABLE_ENTITY_EXTRACTION and paper_data.get("figures"):
        for figure in paper_data["figures"]:
            if "caption" in figure and len(figure["caption"]) > 20:
                try:
                    entities = fetch_entities_from_bern(figure["caption"])
                    figure["entities"] = entities
                except Exception as e:
                    logger.error(f"Error extracting entities from caption: {e}")
                    figure["entities"] = []
            else:
                figure["entities"] = []
    
    # Insert into database
    conn = init_db(DUCKDB_PATH)
    insert_paper(conn, paper_data)
    conn.close()
    
    logger.info(f"Successfully processed and stored paper ID: {pmc_id}")
    return paper_data
