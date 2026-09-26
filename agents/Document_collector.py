import requests
import xml.etree.ElementTree as ET
from typing import List, Dict
from pathlib import Path
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class DocumentCollector:
    def search_arxiv(self, query: str, max_results: int = 10) -> List[Dict]:
        print("**arxiv**")
        """Search arXiv for papers matching the given query."""
        url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        response = requests.get(url, params=params)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        results = []
        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns).text.strip()
            summary = entry.find("atom:summary", ns).text.strip()
            pdf_link = None
            for link in entry.findall("atom:link", ns):
                if link.get("title") == "pdf":
                    pdf_link = link.get("href")
                    break

            results.append({"title": title, "summary": summary, "pdf_url": pdf_link})
            print(f"* {title}")

        return results

    def search_semantic_scholar(self, query: str, max_results: int = 10) -> List[Dict]:
        print("**semantic_scholar**")
        """Search Semantic Scholar for papers matching the given query."""
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,abstract,openAccessPdf",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (research-assistant-app/1.0)",
            "x-api-key": os.getenv("SEMANTIC_SCHOLAR_API_KEY", ""),
        }
        print(f"[DocumentCollector] API key loaded: {bool(os.getenv('SEMANTIC_SCHOLAR_API_KEY'))}")

        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        results = []
        for paper in data.get("data", []):
            pdf_info = paper.get("openAccessPdf")
            pdf_url = pdf_info.get("url") if pdf_info else None
            if not pdf_url:
                continue  # skip papers without a downloadable PDF

            results.append({
                "title": paper.get("title", "Untitled"),
                "summary": paper.get("abstract") or "No abstract available.",
                "pdf_url": pdf_url,
            })    
            print(f"* {paper.get("title", "Untitled")}")

        return results

    def search_pubmed(self, query: str, max_results: int = 10) -> List[Dict]:
        print("**pubmed**")
        """Search PubMed for papers matching the given query.
        Note: most PubMed entries don't have a free full-text PDF; we only
        keep ones with a PMC (PubMed Central) full-text link.
        """
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            "db": "pmc",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
        }
        search_response = requests.get(search_url, params=search_params, timeout=15)
        search_response.raise_for_status()
        ids = search_response.json().get("esearchresult", {}).get("idlist", [])

        results = []
        for pmc_id in ids:
            summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            summary_params = {"db": "pmc", "id": pmc_id, "retmode": "json"}
            summary_response = requests.get(summary_url, params=summary_params, timeout=15)
            summary_response.raise_for_status()
            doc = summary_response.json().get("result", {}).get(pmc_id, {})

            title = doc.get("title", "Untitled")
            pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/"

            results.append({
                "title": title,
                "summary": "Abstract not fetched — see PMC link for full text.",
                "pdf_url": pdf_url,
            })
            print(f"* {title} \n ")

        return results

    def search_by_source(self, source: str, query: str, max_results: int = 10) -> List[Dict]:
        """Dispatch the search to the correct source based on the Planner's choice."""
        try:
            if source == "arxiv":
                return self.search_arxiv(query, max_results)
            elif source == "pubmed":
                return self.search_pubmed(query, max_results)
            else:
                return self.search_semantic_scholar(query, max_results)
                # return self.search_arxiv(query, max_results)

        except Exception as e:
            print(f"[DocumentCollector] {source} failed ({e}), falling back to arxiv")
            if source == "arxiv":
                return []  # arxiv itself failed, nothing left to fall back to
            return self.search_arxiv(query, max_results)

    def search_by_keywords(self, keywords: List[str], source: str = "arxiv", candidate_pool: int = 10) -> List[Dict]:
        """Combine keywords into a single query and fetch a pool of candidates
        from the given source (more than the final desired count, so they can
        be filtered for relevance later).
        """
        combined_query = " ".join(keywords)
        return self.search_by_source(source, combined_query, candidate_pool)

    def download_papers(self, papers: List[Dict], save_dir: str = "uploads") -> List[str]:
        """Download each paper's PDF to disk and return the list of saved file paths."""
        save_path = Path(save_dir)
        save_path.mkdir(exist_ok=True)

        file_paths = []
        for paper in papers:
            pdf_url = paper.get("pdf_url")
            if not pdf_url:
                continue

            try:
                response = requests.get(pdf_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                response.raise_for_status()

                content_type = response.headers.get("Content-Type", "")
                is_pdf_content_type = "application/pdf" in content_type.lower()
                is_pdf_magic_bytes = response.content[:5] == b"%PDF-"

                if not (is_pdf_content_type or is_pdf_magic_bytes):
                    print(f"[DocumentCollector] Skipping '{paper['title']}' — not a real PDF (content-type: {content_type})")
                    continue

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")
                safe_title = "".join(c for c in paper["title"][:50] if c.isalnum() or c in " _-").strip()
                file_path = save_path / f"paper_{timestamp}_{safe_title}.pdf"

                with open(file_path, "wb") as f:
                    f.write(response.content)

                file_paths.append(str(file_path))
            except Exception as e:
                print(f"[DocumentCollector] Failed to download '{paper.get('title', 'unknown')}': {e}")
                continue

        return file_paths