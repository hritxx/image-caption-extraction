import os
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import WATCH_FOLDER, BATCH_SIZE
from extractor import process_paper_id, check_pmc_id_exists, get_pmcid_from_database
from help import convert_pmid_to_pmcid, search_pubmed

logger = logging.getLogger(__name__)

class PaperIDFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        if file_path.endswith('.txt'):
            logger.info(f"New file detected: {file_path}")
            self.process_file(file_path)

    def examine_error_responses(self):
        """Examine error response files to better understand failures"""
        # Get a list of all response XML files in the current directory
        import glob
        response_files = glob.glob("PMC*_response.xml")
        
        for file_path in response_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(500)  # Read first 500 characters
                    
                # Check for error patterns
                if "<ERROR>" in content:
                    error_start = content.find("<ERROR>") + 8
                    error_end = content.find("</ERROR>")
                    error_msg = content[error_start:error_end] if error_end > 0 else "Unknown error"
                    logger.error(f"File {file_path} contains NCBI error: {error_msg}")
                elif "Resource not found" in content:
                    logger.error(f"File {file_path} indicates resource not found")
                elif "DOCTYPE html" in content:
                    logger.error(f"File {file_path} contains HTML instead of XML - likely an error page")
                elif content.strip() == "":
                    logger.error(f"File {file_path} is empty")
                
                # Optionally delete old response files to avoid confusion
                # import os
                # os.remove(file_path)
                
            except Exception as e:
                logger.error(f"Error examining response file {file_path}: {e}")

    def process_file(self, file_path):
        try:
            with open(file_path, 'r') as f:
                paper_ids = [line.strip() for line in f if line.strip()]

            logger.info(f"Found {len(paper_ids)} paper IDs in {file_path}")
            
            # Check response files first if we've had failures
            self.examine_error_responses()
            
            available_papers, unavailable_papers = self.check_available_papers(paper_ids)

            success_count = 0
            fail_count = 0
            skipped_count = len(unavailable_papers)

            for i in range(0, len(available_papers), BATCH_SIZE):
                batch = available_papers[i:i + BATCH_SIZE]
                logger.info(f"Processing batch of {len(batch)} papers")

                for paper_info in batch:
                    paper_id = paper_info['id']
                    pmcid = paper_info['pmcid']
                    try:
                        logger.info(f"Processing paper ID {paper_id} (PMCID {pmcid})")
                        result = process_paper_id(pmcid)

                        if result:
                            fig_count = len(result.get('figures', []))
                            ent_count = sum(len(fig.get('entities', [])) for fig in result.get('figures', []))
                            logger.info(f"Paper {paper_id}: {fig_count} figures, {ent_count} entities")

                        success_count += 1
                    except Exception as e:
                        fail_count += 1
                        logger.error(f"Failed to process {paper_id}: {e}")

            with open(file_path + ".processed", 'w') as f:
                f.write(f"Total: {len(paper_ids)}\nAvailable: {len(available_papers)}\n")
                f.write(f"Success: {success_count}\nFailed: {fail_count}\nSkipped: {skipped_count}\n")

            logger.info(f"Completed processing {file_path}")
            os.rename(file_path, file_path + ".completed")

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            os.rename(file_path, file_path + ".failed")

    def check_available_papers(self, paper_ids):
        """Check which papers are available in PMC with proper validation"""
        from help import search_pubmed, convert_pmid_to_pmcid
        from extractor import check_pmc_id_exists, get_pmcid_from_database

        available = []
        unavailable = []

        for paper_id in paper_ids:
            try:
                # 1. If it's already a PMCID, verify it
                if paper_id.upper().startswith("PMC"):
                    if check_pmc_id_exists(paper_id):
                        available.append({"id": paper_id, "pmcid": paper_id})
                        logger.info(f"{paper_id} is a valid PMCID.")
                    else:
                        logger.warning(f"{paper_id} is not a valid PMCID.")
                        unavailable.append(paper_id)
                    continue

                # 2. Try local database lookup
                db_pmcid = get_pmcid_from_database(paper_id)
                if db_pmcid:
                    # Ensure PMCID has PMC prefix
                    if not db_pmcid.upper().startswith("PMC"):
                        db_pmcid = f"PMC{db_pmcid}"
                        
                    available.append({"id": paper_id, "pmcid": db_pmcid})
                    logger.info(f"Found PMCID {db_pmcid} for PMID {paper_id} in local database.")
                    continue

                # 3. Try NCBI E-utilities conversion
                api_pmcid = convert_pmid_to_pmcid(paper_id)
                if api_pmcid:
                    # API should return PMCID with PMC prefix, but ensure it
                    if not api_pmcid.upper().startswith("PMC"):
                        api_pmcid = f"PMC{api_pmcid}"
                        
                    if check_pmc_id_exists(api_pmcid):
                        available.append({"id": paper_id, "pmcid": api_pmcid})
                        logger.info(f"Converted PMID {paper_id} to PMCID {api_pmcid} via API.")
                        continue
                    else:
                        logger.warning(f"Conversion found PMCID {api_pmcid} for PMID {paper_id}, but it's not accessible in PMC.")
                else:
                    logger.warning(f"Failed to convert PMID {paper_id} to a PMCID.")

                # 4. Try searching PubMed just to check if the ID exists
                results = search_pubmed(f"[uid] {paper_id}", max_results=1)
                if results:
                    logger.warning(f"{paper_id} found in PubMed but has no Open Access PMC version.")
                else:
                    logger.warning(f"{paper_id} not found in PubMed at all.")

                unavailable.append(paper_id)

            except Exception as e:
                logger.error(f"Error resolving {paper_id}: {e}")
                unavailable.append(paper_id)

        logger.info(f"Found {len(available)}/{len(paper_ids)} papers available in PMC.")
        return available, unavailable

   
def start_watcher():
    os.makedirs(WATCH_FOLDER, exist_ok=True)
    observer = Observer()
    observer.schedule(PaperIDFileHandler(), WATCH_FOLDER, recursive=False)
    logger.info(f"Watching folder: {WATCH_FOLDER}")
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("Watcher stopped")
    observer.join()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_watcher()
