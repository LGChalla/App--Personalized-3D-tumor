"""
collectors/pubmed.py
Pulls breast cancer literature from PubMed Entrez API.
Source: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
No registration required. Optional: set NCBI_API_KEY for higher rate limits.
"""

import os
import xml.etree.ElementTree as ET
from .base import BaseCollector

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# High-impact search queries for breast cancer
SEARCH_QUERIES = {
    "survival_by_stage":       'breast+neoplasms[MeSH]+AND+survival[MeSH]+AND+review[pt]',
    "her2_targeted_therapy":   'trastuzumab[tiab]+AND+breast+cancer[MeSH]+AND+clinical+trial[pt]',
    "tnbc_treatment":          '"triple negative breast cancer"[tiab]+AND+treatment[MeSH]+AND+review[pt]',
    "er_positive_therapy":     '"hormone receptor positive"[tiab]+AND+breast+cancer+AND+aromatase+inhibitor',
    "brca_mutations":          'BRCA1[gene]+AND+BRCA2[gene]+AND+breast+cancer+AND+review[pt]',
    "cdk46_inhibitors":        'palbociclib+OR+ribociclib+OR+abemaciclib+AND+breast+cancer',
    "neoadjuvant_chemotherapy":'neoadjuvant+AND+breast+cancer[MeSH]+AND+pathological+complete+response',
    "breast_cancer_prognosis": 'breast+neoplasms[MeSH]+AND+prognosis[MeSH]+AND+review[pt]',
    "predict_tool":            'PREDICT[tiab]+AND+breast+cancer+AND+survival+AND+validation',
    "immunotherapy_breast":    'pembrolizumab+AND+breast+cancer+AND+clinical+trial',
}


class PubMedCollector(BaseCollector):
    """
    Collects:
      - PMIDs for key breast cancer topics
      - Abstracts and metadata for top papers
      - Citation counts (via PubMed)
    """

    def __init__(self, output_dir: str = "data/literature"):
        super().__init__(output_dir, rate_limit_seconds=0.4)
        api_key = os.getenv("NCBI_API_KEY", "")
        if api_key:
            self.session.params = {"api_key": api_key}
            self.rate_limit = 0.1  # 10 requests/sec with API key
        else:
            print("[PubMed] NCBI_API_KEY not set. Rate limited to 3 req/sec.")

    def search(self, query: str, max_results: int = 20) -> list:
        data = self.get(
            f"{BASE_URL}/esearch.fcgi",
            params={
                "db":      "pubmed",
                "term":    query,
                "retmax":  max_results,
                "retmode": "json",
                "sort":    "relevance",
            }
        )
        if data:
            return data.get("esearchresult", {}).get("idlist", [])
        return []

    def fetch_abstracts(self, pmids: list) -> list:
        if not pmids:
            return []
        data = self.get(
            f"{BASE_URL}/efetch.fcgi",
            params={
                "db":      "pubmed",
                "id":      ",".join(pmids),
                "retmode": "xml",
                "rettype": "abstract",
            }
        )
        return self._parse_xml_articles(data) if data else []

    def _parse_xml_articles(self, xml_text) -> list:
        """Parses PubMed XML response."""
        articles = []
        try:
            if isinstance(xml_text, dict):
                return []
            root = ET.fromstring(str(xml_text))
            for article in root.findall(".//PubmedArticle"):
                try:
                    pmid    = article.findtext(".//PMID", "")
                    title   = article.findtext(".//ArticleTitle", "")
                    journal = article.findtext(".//Journal/Title", "")
                    year    = article.findtext(".//PubDate/Year", "")
                    abstract_texts = [a.text or "" for a in article.findall(".//AbstractText")]
                    abstract = " ".join(abstract_texts)
                    authors = [
                        f"{a.findtext('LastName','')} {a.findtext('Initials','')}".strip()
                        for a in article.findall(".//Author")[:5]
                    ]
                    articles.append({
                        "pmid":     pmid,
                        "title":    title,
                        "journal":  journal,
                        "year":     year,
                        "authors":  authors,
                        "abstract": abstract[:1500],
                        "url":      f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    })
                except Exception:
                    continue
        except ET.ParseError as e:
            print(f"  [XML parse error] {e}")
        return articles

    def collect(self, queries: dict = None, max_per_query: int = 10, **kwargs):
        queries = queries or SEARCH_QUERIES
        all_articles = {}

        for topic, query in queries.items():
            print(f"\n[PubMed] {topic}...")
            pmids = self.search(query, max_results=max_per_query)
            if not pmids:
                print(f"  No results")
                continue
            print(f"  {len(pmids)} PMIDs found. Fetching abstracts...")

            # Fetch via efetch (returns XML — handle differently)
            r = self.session.get(
                f"{BASE_URL}/efetch.fcgi",
                params={
                    "db": "pubmed", "id": ",".join(pmids),
                    "retmode": "xml", "rettype": "abstract",
                },
                timeout=30
            )
            articles = []
            if r.status_code == 200:
                articles = self._parse_xml_articles(r.text)

            all_articles[topic] = {
                "query":    query,
                "n_found":  len(pmids),
                "articles": articles,
            }
            print(f"  Parsed {len(articles)} articles")
            self.save(all_articles[topic], f"pubmed_{topic}.json")

        # Master index
        index = {
            topic: {
                "n_articles": len(v["articles"]),
                "pmids": [a["pmid"] for a in v["articles"]],
                "top_paper": v["articles"][0]["title"] if v["articles"] else "",
            }
            for topic, v in all_articles.items()
        }
        self.save(index, "pubmed_index.json")
        return all_articles
