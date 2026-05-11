"""
collectors/fda.py
Pulls FDA-approved breast cancer drug labels from OpenFDA.
Source: https://open.fda.gov/apis/drug/label/
No registration required.
"""

from .base import BaseCollector

BASE_URL = "https://api.fda.gov/drug"

BREAST_CANCER_DRUGS = [
    "tamoxifen", "anastrozole", "letrozole", "exemestane",
    "fulvestrant", "trastuzumab", "pertuzumab", "ado-trastuzumab",
    "trastuzumab deruxtecan", "palbociclib", "ribociclib", "abemaciclib",
    "olaparib", "talazoparib", "sacituzumab", "pembrolizumab",
    "alpelisib", "elacestrant", "doxorubicin", "paclitaxel",
    "docetaxel", "cyclophosphamide", "capecitabine", "carboplatin",
    "eribulin", "ixabepilone", "neratinib", "lapatinib", "tucatinib"
]


class FDACollector(BaseCollector):
    """
    Collects:
      - Full drug labels (indications, dosing, side effects, contraindications)
      - Drug approval history
      - Adverse event summaries
    """

    def __init__(self, output_dir: str = "data/medications"):
        super().__init__(output_dir, rate_limit_seconds=0.4)

    def get_drug_label(self, drug_name: str) -> dict:
        """Fetches full prescribing information from DailyMed via OpenFDA."""
        data = self.get(
            f"{BASE_URL}/label.json",
            params={
                "search": f'openfda.brand_name:"{drug_name}"+OR+openfda.generic_name:"{drug_name}"',
                "limit": 1,
            }
        )
        if data and data.get("results"):
            return data["results"][0]
        # Fallback: search indications text
        data = self.get(
            f"{BASE_URL}/label.json",
            params={
                "search": f'indications_and_usage:"{drug_name}"+AND+indications_and_usage:"breast+cancer"',
                "limit": 1,
            }
        )
        if data and data.get("results"):
            return data["results"][0]
        return {}

    def get_adverse_events(self, drug_name: str, limit: int = 100) -> list:
        """Fetches adverse event reports from FAERS."""
        data = self.get(
            f"{BASE_URL}/event.json",
            params={
                "search":   f'patient.drug.openfda.generic_name:"{drug_name}"',
                "count":    "patient.reaction.reactionmeddrapt.exact",
                "limit":    limit,
            }
        )
        if data and data.get("results"):
            return data["results"]
        return []

    def get_approvals_history(self) -> list:
        """Fetches FDA oncology approvals mentioning breast cancer."""
        data = self.get(
            f"{BASE_URL}/label.json",
            params={
                "search": "indications_and_usage:breast+cancer",
                "limit":  100,
            }
        )
        if data and data.get("results"):
            return data["results"]
        return []

    def parse_label(self, label: dict) -> dict:
        """Extracts the most clinically useful fields from a drug label."""
        openfda = label.get("openfda", {})
        return {
            "brand_name":              openfda.get("brand_name", ["Unknown"])[0] if openfda.get("brand_name") else "Unknown",
            "generic_name":            openfda.get("generic_name", ["Unknown"])[0] if openfda.get("generic_name") else "Unknown",
            "manufacturer":            openfda.get("manufacturer_name", ["Unknown"])[0] if openfda.get("manufacturer_name") else "Unknown",
            "route":                   openfda.get("route", []),
            "indications":             label.get("indications_and_usage", [""])[0][:2000] if label.get("indications_and_usage") else "",
            "dosage":                  label.get("dosage_and_administration", [""])[0][:1000] if label.get("dosage_and_administration") else "",
            "warnings":                label.get("warnings_and_cautions", label.get("warnings", [""]))[0][:1000] if label.get("warnings_and_cautions") or label.get("warnings") else "",
            "adverse_reactions":       label.get("adverse_reactions", [""])[0][:1000] if label.get("adverse_reactions") else "",
            "contraindications":       label.get("contraindications", [""])[0][:500] if label.get("contraindications") else "",
            "mechanism_of_action":     label.get("mechanism_of_action", [""])[0][:500] if label.get("mechanism_of_action") else "",
            "drug_interactions":       label.get("drug_interactions", [""])[0][:500] if label.get("drug_interactions") else "",
            "pregnancy":               label.get("pregnancy", [""])[0][:300] if label.get("pregnancy") else "",
        }

    def collect(self, drugs: list = None, **kwargs):
        drugs = drugs or BREAST_CANCER_DRUGS
        all_labels = []

        print(f"\n[FDA] Fetching labels for {len(drugs)} breast cancer drugs")
        for drug in drugs:
            print(f"  {drug}...", end=" ", flush=True)
            raw = self.get_drug_label(drug)
            if raw:
                parsed = self.parse_label(raw)
                parsed["query_term"] = drug
                all_labels.append(parsed)
                print(f"OK — {parsed['brand_name']} / {parsed['generic_name']}")
            else:
                print("not found")

        self.save(all_labels, "fda_breast_drug_labels.json")
        print(f"\n  Collected {len(all_labels)} drug labels")
        return all_labels
