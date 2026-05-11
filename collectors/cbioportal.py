"""
collectors/cbioportal.py
Pulls breast cancer genomic data from cBioPortal API.
Source: https://www.cbioportal.org/api/swagger-ui/index.html
No registration required.
"""

from .base import BaseCollector

BASE_URL = "https://www.cbioportal.org/api"

BREAST_STUDIES = [
    "brca_tcga",           # TCGA Breast — 1,084 samples
    "brca_tcga_pan_can_atlas_2018",  # TCGA PanCancer — 1,084 samples
    "brca_metabric",       # METABRIC — 2,509 samples
    "breast_msk_2018",     # MSK — 3,000+ samples
]

KEY_GENES = [
    "TP53", "PIK3CA", "CDH1", "GATA3", "MAP3K1",
    "ERBB2", "ESR1", "BRCA1", "BRCA2", "PTEN",
    "AKT1", "CCND1", "MYC", "RB1", "CDKN2A",
    "KRAS", "NF1", "TBX3", "RUNX1", "SF3B1"
]


class CBioPortalCollector(BaseCollector):
    """
    Collects:
      - Study metadata and sample counts
      - Mutation frequencies for key breast cancer genes
      - Clinical data (ER, PR, HER2, stage, OS)
      - Survival data by molecular subtype
    """

    def __init__(self, output_dir: str = "data/genomic"):
        super().__init__(output_dir, rate_limit_seconds=0.3)

    def get_studies(self) -> list:
        print("Fetching breast cancer studies...")
        data = self.get(f"{BASE_URL}/studies", params={"keyword": "breast", "pageSize": 50})
        if data:
            studies = [s for s in data if any(k in s.get("studyId","").lower()
                                               for k in ("brca","breast"))]
            print(f"  Found {len(studies)} breast cancer studies")
            return studies
        return []

    def get_clinical_data(self, study_id: str) -> list:
        print(f"  Fetching clinical data: {study_id}")
        data = self.get(
            f"{BASE_URL}/studies/{study_id}/clinical-data",
            params={"clinicalDataType": "PATIENT", "pageSize": 5000}
        )
        return data or []

    def get_mutations(self, study_id: str, genes: list = None) -> list:
        genes = genes or KEY_GENES
        print(f"  Fetching mutations: {study_id} ({len(genes)} genes)")
        data = self.get(
            f"{BASE_URL}/molecular-profiles/{study_id}_mutations/mutations",
            params={
                "entrezGeneIds": ",".join(str(g) for g in self._resolve_gene_ids(genes)),
                "pageSize": 10000
            }
        )
        return data or []

    def get_mutation_frequency(self, study_id: str) -> list:
        """Returns mutation frequency per gene across the study."""
        print(f"  Fetching mutation spectrum: {study_id}")
        data = self.get(
            f"{BASE_URL}/studies/{study_id}/molecular-profiles",
        )
        return data or []

    def get_sample_counts(self, study_id: str) -> dict:
        data = self.get(f"{BASE_URL}/studies/{study_id}")
        return data or {}

    def _resolve_gene_ids(self, symbols: list) -> list:
        """Converts gene symbols to Entrez IDs via cBioPortal gene endpoint."""
        ids = []
        for sym in symbols:
            data = self.get(f"{BASE_URL}/genes/{sym}")
            if data and "entrezGeneId" in data:
                ids.append(data["entrezGeneId"])
        return ids

    def get_survival_data(self, study_id: str) -> list:
        """Fetches overall survival and disease-free survival."""
        print(f"  Fetching survival: {study_id}")
        os_data = self.get(
            f"{BASE_URL}/studies/{study_id}/clinical-data",
            params={"attributeId": "OS_STATUS,OS_MONTHS,DFS_STATUS,DFS_MONTHS",
                    "clinicalDataType": "PATIENT", "pageSize": 5000}
        )
        return os_data or []

    def collect(self, study_ids: list = None, **kwargs):
        study_ids = study_ids or BREAST_STUDIES
        results = {}

        for study_id in study_ids:
            print(f"\n[cBioPortal] Study: {study_id}")
            results[study_id] = {
                "metadata":      self.get_sample_counts(study_id),
                "clinical_data": self.get_clinical_data(study_id),
                "survival":      self.get_survival_data(study_id),
            }
            self.save(results[study_id], f"cbioportal_{study_id}.json")

        # Summary across all studies
        summary = {sid: {
            "n_patients": r["metadata"].get("allSampleCount", 0),
            "name":       r["metadata"].get("name", sid),
        } for sid, r in results.items()}
        self.save(summary, "cbioportal_studies_summary.json")
        return results
