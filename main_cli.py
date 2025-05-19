import argparse
import requests
import os
from config import DUCKDB_PATH
import duckdb
from extractor import process_paper_id  # Import the fetch function for direct testing

API_URL = "http://localhost:8000"
API_KEY = os.getenv("API_KEY", "your-default-api-key")

def submit_ids(file_path):
    with open(file_path) as f:
        ids = [line.strip() for line in f if line.strip()]
    resp = requests.post(f"{API_URL}/extract", json={"paper_ids": ids},
                         headers={"X-API-Key": API_KEY})
    print(resp.json())

def get_paper(paper_id):
    resp = requests.get(f"{API_URL}/papers/{paper_id}", headers={"X-API-Key": API_KEY})
    print(resp.json())

def test_fetch(paper_id):
    print(f"Directly testing fetch+entity-extract for {paper_id}...")
    try:
        result = process_paper_id(paper_id)
        if result:
            print(f"Success! Found paper with title: {result.get('title', 'No title')[:50]}...")
            print(f"Extracted {len(result['figures'])} figures with entities.")
        else:
            print(f"Failed to process paper {paper_id}")
    except Exception as e:
        print(f"Error processing paper {paper_id}: {str(e)}")
        

def list_all_papers():
    """List all papers in the database directly"""
    resp = requests.get(f"{API_URL}/papers", headers={"X-API-Key": API_KEY})
    papers = resp.json()
    
    if not papers:
        print("No papers found in the database.")
        return
        
    print(f"Found {len(papers)} papers:")
    for paper in papers:
        print(f"- {paper['pmcid']}: {paper['title'][:50]}...")
    
    

def view_db():
    """View the raw database contents using DuckDB"""
    try:
        conn = duckdb.connect(DUCKDB_PATH)
        results = conn.execute("SELECT * FROM publications").fetchall()
        
        if not results:
            print("No publications found in the database.")
            return
            
        print(f"Found {len(results)} publications:")
        for result in results:
            pmcid, title, abstract, figures = result
            print(f"- {pmcid}: {title[:50]}...")
            print(f"  Abstract: {abstract[:100]}...")
            print(f"  Figures: {len(figures) if figures else 0}")
            print()
        
    except Exception as e:
        print(f"Error accessing database: {e}")
    finally:
        if 'conn' in locals():
            conn.close()


def diagnose_system():
    """Run diagnostic tests on the paper extractor system"""
    print("🔍 Running system diagnostics...\n")
    
    # 1. Check database connection
    print("⚙️  Testing database connection...")
    try:
        conn = duckdb.connect(DUCKDB_PATH)
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        conn.close()
        print(f"✅ Database connection successful. Found {len(table_names)} tables: {', '.join(table_names)}")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
    
    # 2. Test BERN API connection
    print("\n⚙️  Testing BERN entity extraction API...")
    from extractor import fetch_entities_from_bern
    test_caption = "COVID-19 patients showed increased levels of IL-6 and TNF-alpha."
    try:
        entities = fetch_entities_from_bern(test_caption)
        if entities:
            print(f"✅ BERN API connection successful. Found {len(entities)} entities.")
            for entity in entities[:3]:  # Show first 3 entities
                print(f"   - {entity['text']} ({entity['type']})")
            if len(entities) > 3:
                print(f"   - ... and {len(entities) - 3} more")
        else:
            print("⚠️  BERN API connection worked but no entities were found.")
    except Exception as e:
        print(f"❌ BERN API connection failed: {e}")
    
    # 3. Test PMID to PMCID conversion
    print("\n⚙️  Testing PMID to PMCID conversion...")
    try:
        from help import convert_pmid_to_pmcid
        test_pmid = "33621649"  # PMID for a known COVID paper
        pmcid = convert_pmid_to_pmcid(test_pmid)
        if pmcid:
            print(f"✅ PMID to PMCID conversion successful: {test_pmid} → {pmcid}")
        else:
            print(f"⚠️  PMID to PMCID conversion failed to find a match for {test_pmid}")
    except Exception as e:
        print(f"❌ PMID to PMCID conversion failed: {e}")
    
    # 4. Test BioC API connection
    print("\n⚙️  Testing BioC API connection...")
    from extractor import fetch_bioc_paper
    test_pmcid = "PMC7877219"  # Known working PMC ID
    try:
        paper = fetch_bioc_paper(test_pmcid)
        if paper:
            print(f"✅ BioC API connection successful. Retrieved paper titled: \"{paper['title'][:50]}...\"")
            print(f"   Found {len(paper['figures'])} figures and {len(paper['abstract'])} characters in abstract")
        else:
            print(f"⚠️  BioC API connection worked but no data was retrieved for {test_pmcid}")
    except Exception as e:
        print(f"❌ BioC API connection failed: {e}")
    
    print("\n🔍 Diagnostics complete!")
 
 
def search_articles(query, max_results=10):
    """Search for articles in PubMed"""
    print(f"Searching PubMed for: {query}")
    from help import search_pubmed
    
    results = search_pubmed(query, max_results)
    
    if not results:
        print("No results found.")
        return
        
    print(f"Found {len(results)} articles:")
    for i, article in enumerate(results, 1):
        print(f"{i}. {article['title']}")
        print(f"   PMID: {article['pmid']}")
        print(f"   Authors: {', '.join(article['authors'][:3])}{' and others' if len(article['authors']) > 3 else ''}")
        print(f"   Journal: {article['journal']}")
        print(f"   Published: {article['publication_date']}")
        if article['doi']:
            print(f"   DOI: {article['doi']}")
        print()
        
    # Ask user if they want to process any of these articles
    selection = input("Enter an article number to extract it (or press Enter to skip): ")
    if selection and selection.isdigit() and 1 <= int(selection) <= len(results):
        pmid = results[int(selection)-1]['pmid']
        print(f"Extracting article with PMID: {pmid}")
        test_fetch(pmid)
   

# In the main section, add:
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", help="Search PubMed for articles")
    parser.add_argument("--max-results", type=int, default=10, help="Maximum number of search results to display")
    parser.add_argument("--file", help="Path to file with paper IDs")
    parser.add_argument("--get", help="Get paper data by ID")
    parser.add_argument("--test", help="Test fetching a paper ID directly")
    parser.add_argument("--list", action="store_true", help="List all papers in the database")
    parser.add_argument("--db", action="store_true", help="View raw database contents")
    parser.add_argument("--diagnose", action="store_true", help="Run system diagnostics")
    parser.add_argument("--debug-search", help="Debug PubMed search API responses")

    args = parser.parse_args()

    if args.file:
        submit_ids(args.file)
    elif args.get:
        get_paper(args.get)
    elif args.test:
        test_fetch(args.test)
    elif args.search:
        search_articles(args.search, args.max_results)
    elif args.debug_search:
        from help import debug_ncbi_response
        debug_ncbi_response(args.debug_search)
    elif args.list:
        list_all_papers()
    elif args.db:
        view_db()
    elif args.diagnose:
        diagnose_system()
    else:
        parser.print_help()