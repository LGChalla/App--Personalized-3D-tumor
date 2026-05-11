"""
collectors/oncokb.py
Pulls breast cancer biomarker-drug actionability from OncoKB.
Source: https://api.oncokb.org/
Requires free registration at oncokb.org to get API token.
Set env var: ONCOKB_TOKEN=your_token
"""

import os
from .base import BaseCollector

BASE_URL = "https://api.oncokb.org/api/v1"

BREAST_BIOMARKERS = [
    # Receptor status
    {"gene": "ERBB2", "alteration": "Amplification"},
    {"gene": "ESR1",  "alteration": "Mutation"},
    {"gene": "ESR1",  "alteration": "p.Y537S"},
    {"gene": "ESR1",  "alteration": "p.D538G"},
    # PIK3CA
    {"gene": "PIK3CA", "alteration": "Mutation"},
    {"gene": "PIK3CA", "alteration": "p.H1047R"},
    {"gene": "PIK3CA", "alteration": "p.E545K"},
    # BRCA
    {"gene": "BRCA1", "alteration": "Mutation"},
    {"gene": "BRCA2", "alteration": "Mutation"},
    # CDK4/6 pathway
    {"gene": "CCND1", "alteration": "Amplification"},
    {"gene": "CDK4",  "alteration": "Amplification"},
    # Immunotherapy
    {"gene": "TMB",   "alteration": "High"},
    {"gene": "CD274", "alteration": "Overexpression"},   # PD-L1
    # NTRK
    {"gene": "NTRK1", "alteration": "Fusion"},
    {"gene": "NTRK3", "alteration": "Fusion"},
    # Other actionable
    {"gene": "AKT1",  "alteration": "p.E17K"},
    {"gene": "PTEN",  "alteration": "Deletion"},
]


class OncoKBCollector(BaseCollector):
    """
    Collects:
      - Biomarker actionability levels (1, 2, 3A, 3B, 4, R1, R2)
      - FDA-approved treatments per biomarker
      - Clinical evidence summaries
    """

    def __init__(self, output_dir: str = "data/biomarkers"):
        super().__init__(output_dir, rate_limit_seconds=0.5)
        token = os.getenv("ONCOKB_TOKEN", "")
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            print("[OncoKB] ONCOKB_TOKEN not set. Register at oncokb.org for free access.")

    def get_gene_summary(self, gene: str) -> dict:
        return self.get(f"{BASE_URL}/genes/{gene}") or {}

    def get_actionability(self, gene: str, alteration: str,
                          tumor_type: str = "Breast Cancer") -> dict:
        return self.get(
            f"{BASE_URL}/annotate/mutations/byProteinChange",
            params={
                "hugoSymbol":       gene,
                "alteration":       alteration,
                "tumorType":        tumor_type,
                "referenceGenome":  "GRCh37",
            }
        ) or {}

    def get_approved_drugs_for_cancer(self, cancer_type: str = "Breast Cancer") -> list:
        data = self.get(
            f"{BASE_URL}/treatments",
            params={"cancerType": cancer_type}
        )
        return data or []

    def collect(self, **kwargs):
        results = []
        print(f"\n[OncoKB] Fetching actionability for {len(BREAST_BIOMARKERS)} breast cancer biomarkers")

        for bm in BREAST_BIOMARKERS:
            gene = bm["gene"]
            alt  = bm["alteration"]
            print(f"  {gene} {alt}...", end=" ", flush=True)

            data = self.get_actionability(gene, alt)
            if not data:
                print("no data")
                continue

            oncogenic    = data.get("oncogenic", "Unknown")
            highest_level = data.get("highestSensitiveLevel") or data.get("highestResistanceLevel") or "None"
            treatments   = data.get("treatments", [])

            entry = {
                "gene":          gene,
                "alteration":    alt,
                "oncogenic":     oncogenic,
                "highest_level": highest_level,
                "n_treatments":  len(treatments),
                "treatments": [{
                    "drugs":       [d.get("drugName") for d in t.get("drugs", [])],
                    "level":       t.get("level"),
                    "indication":  t.get("levelAssociatedCancerType", {}).get("mainType", {}).get("name"),
                } for t in treatments],
                "summary": data.get("geneSummary", ""),
                "variant_summary": data.get("variantSummary", ""),
            }
            results.append(entry)
            print(f"level={highest_level} drugs={len(treatments)}")

        self.save(results, "oncokb_breast_biomarkers.json")

        # Also pull approved drugs list
        print("\n  Fetching approved drug list...")
        approved = self.get_approved_drugs_for_cancer()
        self.save(approved, "oncokb_breast_approved_drugs.json")

        return results
