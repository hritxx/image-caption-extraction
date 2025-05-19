import os
import logging
import duckdb
from config import DUCKDB_PATH
from config import NCBI_API_KEY


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def build_pmid_to_pmcid_mapping(mapping_file_path):
    """
    Create a mapping table between PMIDs and PMCIDs from a text file.
    
    Expected format of the file depends on mapping_file_format:
    - Standard: "PMID\tPMCID"
    - OA List: various formats, will attempt to extract PMC IDs
    
    Args:
        mapping_file_path (str): Path to the mapping file
    
    Returns:
        int: Number of mappings added to the database
    """
    if not os.path.exists(mapping_file_path):
        logger.error(f"Mapping file not found: {mapping_file_path}")
        return 0
    
    # Connect to database
    conn = duckdb.connect(DUCKDB_PATH)
    
    # Clear existing mappings
    conn.execute("DROP TABLE IF EXISTS pmid_to_pmcid")
    
    # Create the mapping table
    conn.execute("""
        CREATE TABLE pmid_to_pmcid (
            pmid VARCHAR,
            pmcid VARCHAR,
            PRIMARY KEY (pmid)
        )
    """)
    
    # Read the mapping file and insert into database
    mappings = []
    count = 0
    errors = 0
    
    try:
        with open(mapping_file_path, 'r') as f:
            # Skip the first line if it's a timestamp
            first_line = f.readline().strip()
            if not first_line.startswith('oa_package'):
                line_num = 1  # We already read one line
            else:
                # Reset file pointer if the first line is data
                f.seek(0)
                line_num = 0
                
            for line in f:
                line_num += 1
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                try:
                    # Split the line by tabs
                    parts = line.split('\t')
                    
                    # oa_list.txt format: file_path TAB title TAB PMCID TAB PMID:123456 TAB license
                    if len(parts) >= 4 and 'PMID:' in parts[3]:
                        pmid = parts[3].replace('PMID:', '').strip()
                        pmcid = parts[2].strip()
                        
                        # Ensure PMCID has PMC prefix
                        if not pmcid.startswith('PMC'):
                            pmcid = f"PMC{pmcid}"
                            
                        mappings.append((pmid, pmcid))
                        count += 1
                    
                    # Handle standard PMID\tPMCID format
                    elif len(parts) >= 2 and parts[1].strip().upper().startswith('PMC'):
                        pmid = parts[0].strip()
                        pmcid = parts[1].strip().upper()
                        
                        # Ensure PMCID has PMC prefix
                        if not pmcid.startswith('PMC'):
                            pmcid = f"PMC{pmcid}"
                            
                        mappings.append((pmid, pmcid))
                        count += 1
                    # Extract PMCID from file path if it matches the pattern
                    elif 'PMC' in line:
                        # Extract the PMC ID from string
                        import re
                        pmc_matches = re.findall(r'PMC(\d+)', line)
                        
                        if pmc_matches:
                            pmcid = f"PMC{pmc_matches[0]}"
                            # Use the PMC number as the PMID for now (since we don't have a real PMID)
                            pmid = pmc_matches[0]
                            mappings.append((pmid, pmcid))
                            count += 1
                        else:
                            errors += 1
                    else:
                        errors += 1
                
                except Exception as e:
                    logger.error(f"Error parsing line {line_num}: {line} - {e}")
                    errors += 1
                    continue
                
                # Insert in batches of 1000
                if len(mappings) >= 1000:
                    conn.executemany(
                        "INSERT OR REPLACE INTO pmid_to_pmcid (pmid, pmcid) VALUES (?, ?)",
                        mappings
                    )
                    mappings = []
                    logger.info(f"Inserted 1000 mappings, total so far: {count}")
        
        # Insert any remaining mappings
        if mappings:
            conn.executemany(
                "INSERT OR REPLACE INTO pmid_to_pmcid (pmid, pmcid) VALUES (?, ?)",
                mappings
            )
            
        logger.info(f"Successfully added {count} PMID to PMCID mappings to the database")
        logger.info(f"Encountered {errors} lines that couldn't be parsed")
        return count
    
    except Exception as e:
        logger.error(f"Error building PMID to PMCID mapping: {e}")
        return 0
    
    finally:
        conn.close()
        

def download_pmid_pmcid_mapping():
    """
    Download the official PMID to PMCID mapping file from NCBI.
    
    Returns:
        str: Path to the downloaded file
    """
    import requests
    import tempfile
    
    url = "https://ftp.ncbi.nlm.nih.gov/pub/pmc/PMC-ids.csv.gz"
    output_file = os.path.join(tempfile.gettempdir(), "PMC-ids.csv.gz")
    
    try:
        print(f"Downloading PMID-PMCID mapping file from {url}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Downloaded mapping file to {output_file}")
        return output_file
    
    except Exception as e:
        logger.error(f"Error downloading PMID-PMCID mapping file: {e}")
        return None

# This should be in your help.py file
def convert_pmid_to_pmcid(pmid):
    """Convert a PubMed ID (PMID) to a PubMed Central ID (PMCID) using NCBI's E-utilities."""
    import requests
    import time
    
    # Base URL for ID conversion
    base_url = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
    
    params = {
        "tool": "paper-extractor",
        "email": "hriteekroy1869@gmail.com",  # Should be your email
        "ids": pmid,
        "format": "json"
    }
    
    # Add API key if available
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse the response to extract the PMCID
            if "records" in data and data["records"]:
                for record in data["records"]:
                    if "pmcid" in record:
                        return record["pmcid"]
            
            # No PMCID found
            return None
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                # Wait before retrying
                logger.warning(f"PMID conversion attempt {attempt+1} failed: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Failed to convert PMID {pmid} after {max_retries} attempts: {e}")
                return None

def download_pmid_pmcid_mapping():
    """
    Download the official PMID to PMCID mapping file from NCBI.
    
    Returns:
        str: Path to the downloaded file
    """
    import os
    import tempfile
    import requests
    from config import NCBI_API_KEY
    
    url = "https://ftp.ncbi.nlm.nih.gov/pub/pmc/PMC-ids.csv.gz"
    # For FTP downloads, the API key isn't used in the URL but in the headers
    headers = {"api-key": NCBI_API_KEY} if NCBI_API_KEY else {}
    output_file = os.path.join(tempfile.gettempdir(), "PMC-ids.csv.gz")
    
    try:
        logger.info(f"Downloading PMC ID mapping file from {url}")
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Downloaded mapping file to {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"Error downloading PMC ID mapping file: {e}")
        return None

def search_pubmed(query, max_results=10):
    """
    Search PubMed using NCBI E-utilities.
    
    Args:
        query (str): The search query
        max_results (int): Maximum number of results to return
        
    Returns:
        list: List of dictionaries containing article information
    """
    import requests
    import time
    import json
    from config import NCBI_API_KEY
    
    # Base URL for E-utilities
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    
    # Step 1: Search for PMIDs
    search_url = f"{base_url}esearch.fcgi"
    search_params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "usehistory": "y"
    }
    
    if NCBI_API_KEY:
        search_params["api_key"] = NCBI_API_KEY
    
    try:
        logger.info(f"Searching PubMed for: {query}")
        response = requests.get(search_url, params=search_params)
        response.raise_for_status()
        search_data = response.json()
        
        # Extract PMIDs from search results
        pmids = search_data["esearchresult"].get("idlist", [])
        
        if not pmids:
            logger.warning(f"No results found for query: {query}")
            return []
        
        # Step 2: Fetch article summaries
        fetch_url = f"{base_url}esummary.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json"
        }
        
        if NCBI_API_KEY:
            fetch_params["api_key"] = NCBI_API_KEY
        
        # Add a small delay to avoid overloading the API
        time.sleep(0.3)
        
        logger.info(f"Fetching details for {len(pmids)} results")
        response = requests.get(fetch_url, params=fetch_params)
        response.raise_for_status()
        summary_data = response.json()
        
        # Debug: Save the actual response to a file
        with open('pubmed_response.json', 'w') as f:
            json.dump(summary_data, f, indent=2)
        
        results = []
        for pmid in pmids:
            if pmid not in summary_data["result"]:
                logger.warning(f"No data found for PMID {pmid}")
                continue
                
            article_data = summary_data["result"][pmid]
            
            # Extract article information
            authors_list = article_data.get("authors", [])
            authors = []
            for author in authors_list:
                if isinstance(author, dict) and "name" in author:
                    authors.append(author["name"])
            
            # Extract DOI safely
            doi = ""
            article_ids = article_data.get("articleids", [])
            for id_item in article_ids:
                if isinstance(id_item, dict) and id_item.get("idtype") == "doi":
                    doi = id_item.get("value", "")
                    break
            
            article = {
                "pmid": pmid,
                "title": article_data.get("title", ""),
                "authors": authors,
                "journal": article_data.get("fulljournalname", article_data.get("source", "")),
                "publication_date": article_data.get("pubdate", ""),
                "doi": doi
            }
            
            results.append(article)
        
        logger.info(f"Successfully found {len(results)} articles")
        return results
        
    except Exception as e:
        logger.error(f"Error searching PubMed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def lookup_pmcid(pmid):
    """
    Look up a PMCID for a given PMID from the database.
    
    Args:
        pmid (str): The PMID to look up
        
    Returns:
        str: The corresponding PMCID or None if not found
    """
    try:
        conn = duckdb.connect(DUCKDB_PATH)
        result = conn.execute(
            "SELECT pmcid FROM pmid_to_pmcid WHERE pmid = ?",
            [pmid]
        ).fetchone()
        
        conn.close()
        
        if result:
            return result[0]
        return None
    
    except Exception as e:
        logger.error(f"Error looking up PMCID for PMID {pmid}: {e}")
        return None

def debug_ncbi_response(query, max_results=3):
    """
    Debug function to print the actual structure of NCBI API responses.
    
    Args:
        query (str): The search query
        max_results (int): Maximum number of results to return
    """
    import requests
    import json
    from config import NCBI_API_KEY
    
    # Base URL for E-utilities
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    
    # Step 1: Search for PMIDs
    search_url = f"{base_url}esearch.fcgi"
    search_params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json"
    }
    
    if NCBI_API_KEY:
        search_params["api_key"] = NCBI_API_KEY
    
    print(f"Searching PubMed for: {query}")
    print(f"Request URL: {search_url}")
    print(f"Query parameters: {search_params}")
    
    try:
        response = requests.get(search_url, params=search_params)
        response.raise_for_status()
        search_data = response.json()
        
        print("\n=== SEARCH RESPONSE STRUCTURE ===")
        print(json.dumps(search_data, indent=2)[:500] + "...\n")
        
        pmids = search_data["esearchresult"].get("idlist", [])
        if pmids:
            # Step 2: Fetch article summary for first result only
            fetch_url = f"{base_url}esummary.fcgi"
            fetch_params = {
                "db": "pubmed",
                "id": pmids[0],
                "retmode": "json"
            }
            
            if NCBI_API_KEY:
                fetch_params["api_key"] = NCBI_API_KEY
            
            print(f"Fetching details for PMID {pmids[0]}")
            print(f"Request URL: {fetch_url}")
            print(f"Query parameters: {fetch_params}")
            
            response = requests.get(fetch_url, params=fetch_params)
            response.raise_for_status()
            summary_data = response.json()
            
            # Save full response for examination
            with open('pubmed_debug_response.json', 'w') as f:
                json.dump(summary_data, f, indent=2)
            print(f"Full response saved to pubmed_debug_response.json")
            
            print("\n=== SUMMARY RESPONSE STRUCTURE ===")
            print(json.dumps(summary_data, indent=2)[:1000] + "...\n")
            
            # Direct access to the article data using the PMID key
            if "result" in summary_data and pmids[0] in summary_data["result"]:
                article = summary_data["result"][pmids[0]]
                print("\n=== ARTICLE STRUCTURE ===")
                print(json.dumps(article, indent=2)[:1000] + "...\n")
                
                # Extract and display authors
                authors = []
                for author in article.get("authors", []):
                    if isinstance(author, dict) and "name" in author:
                        authors.append(author["name"])
                
                print(f"PMID: {pmids[0]}")
                print(f"Title: {article.get('title', 'No title')}")
                print(f"Authors: {', '.join(authors)}")
                print(f"Journal: {article.get('fulljournalname', article.get('source', 'Unknown'))}")
                print(f"Publication date: {article.get('pubdate', 'Unknown')}")
            else:
                print(f"Could not find article data for PMID {pmids[0]} in the response")
                print("Available keys in result:", summary_data["result"].keys())
        else:
            print("No PMIDs found in search results")
        
        print("\nDebug complete.")
    except Exception as e:
        print(f"Error during API request: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    import argparse
    
    
    parser = argparse.ArgumentParser(description="Build PMID to PMCID mapping database")
    parser.add_argument("--download", action="store_true", help="Download the official PMID-PMCID mapping file from NCBI")
    parser.add_argument("--file", help="Path to mapping file")
    parser.add_argument("--lookup", help="Look up a PMCID for a given PMID")
    parser.add_argument("--list", action="store_true", help="List first 20 PMID-PMCID mappings in the database")
    parser.add_argument("--count", action="store_true", help="Show the total number of mappings in the database")
    
    args = parser.parse_args()
    
    if args.lookup:
        pmcid = lookup_pmcid(args.lookup)
        if pmcid:
            print(f"PMID {args.lookup} maps to {pmcid}")
        else:
            print(f"No PMCID found for PMID {args.lookup}")
    elif args.file:
        count = build_pmid_to_pmcid_mapping(args.file)
        print(f"Added {count} mappings to the database")
    elif args.list:
        try:
            conn = duckdb.connect(DUCKDB_PATH)
            result = conn.execute("SELECT pmid, pmcid FROM pmid_to_pmcid LIMIT 20").fetchall()
            conn.close()
            
            if result:
                print("First 20 PMID-PMCID mappings:")
                for pmid, pmcid in result:
                    print(f"{pmid} → {pmcid}")
            else:
                print("No mappings found in the database.")
        except Exception as e:
            print(f"Error listing mappings: {e}")
    elif args.download:
        mapping_file = download_pmid_pmcid_mapping()
        if mapping_file:
            print(f"Successfully downloaded mapping file to {mapping_file}")
            print("You can now use this file with --file option:")
            print(f"python help.py --file {mapping_file}")
        else:
            print("Failed to download mapping file.")
    elif args.count:
        try:
            conn = duckdb.connect(DUCKDB_PATH)
            result = conn.execute("SELECT COUNT(*) FROM pmid_to_pmcid").fetchone()
            conn.close()
            
            count = result[0] if result else 0
            print(f"Total PMID-PMCID mappings in database: {count}")
        except Exception as e:
            print(f"Error counting mappings: {e}")
    else:
        parser.print_help()