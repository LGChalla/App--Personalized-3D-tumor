"""
collectors/tcia.py
Downloads breast cancer imaging metadata from The Cancer Imaging Archive (TCIA).
Source: https://www.cancerimagingarchive.net/
No registration required for metadata. Image download requires NBIA Data Retriever.
"""

from .base import BaseCollector

NBIA_BASE  = "https://services.cancerimagingarchive.net/nbia-api/services/v1"
TCIA_BASE  = "https://services.cancerimagingarchive.net/nbia-api/services"

BREAST_COLLECTIONS = [
    {
        "id":          "CBIS-DDSM",
        "name":        "Curated Breast Imaging Subset of DDSM",
        "modality":    "MG",
        "n_subjects":  2620,
        "description": "Mammography with mass/calcification annotations and pathology labels",
        "url":         "https://www.cancerimagingarchive.net/collection/cbis-ddsm/",
        "license":     "CC BY 3.0"
    },
    {
        "id":          "Duke-Breast-Cancer-MRI",
        "name":        "Duke Breast Cancer MRI",
        "modality":    "MR",
        "n_subjects":  922,
        "description": "DCE-MRI with clinical and pathology data for biopsy-confirmed breast cancer",
        "url":         "https://www.cancerimagingarchive.net/collection/duke-breast-cancer-mri/",
        "license":     "CC BY 4.0"
    },
    {
        "id":          "ISPY1",
        "name":        "Investigation of Serial Studies to Predict Your Therapeutic Response",
        "modality":    "MR",
        "n_subjects":  222,
        "description": "Serial DCE-MRI during neoadjuvant chemotherapy with pCR outcomes",
        "url":         "https://www.cancerimagingarchive.net/collection/ispy1/",
        "license":     "TCIA Restricted"
    },
    {
        "id":          "Breast-MRI-NACT-Pilot",
        "name":        "Breast MRI NACT Pilot",
        "modality":    "MR",
        "n_subjects":  64,
        "description": "MRI before/after neoadjuvant chemotherapy",
        "url":         "https://www.cancerimagingarchive.net/collection/breast-mri-nact-pilot/",
        "license":     "CC BY 3.0"
    },
]


class TCIACollector(BaseCollector):
    """
    Collects:
      - Collection metadata (patient counts, modalities, annotations)
      - Series-level metadata (for targeted downloads)
      - Download instructions for each collection
    Note: Actual DICOM image download requires NBIA Data Retriever (GUI tool).
          This collector handles metadata only.
    """

    def __init__(self, output_dir: str = "data/imaging"):
        super().__init__(output_dir, rate_limit_seconds=0.5)

    def get_collections(self) -> list:
        """Lists all available TCIA collections."""
        data = self.get(f"{NBIA_BASE}/getCollectionValues", params={"format": "json"})
        return data or []

    def get_breast_collections(self) -> list:
        all_colls = self.get_collections()
        return [c for c in all_colls
                if any(k in str(c).lower() for k in ("breast", "brca", "mammo", "ddsm"))]

    def get_collection_metadata(self, collection: str) -> dict:
        patient_data = self.get(
            f"{NBIA_BASE}/getPatient",
            params={"Collection": collection, "format": "json"}
        )
        series_data = self.get(
            f"{NBIA_BASE}/getSeries",
            params={"Collection": collection, "format": "json"}
        )
        modalities = self.get(
            f"{NBIA_BASE}/getModalityValues",
            params={"Collection": collection, "format": "json"}
        )
        return {
            "collection":   collection,
            "n_patients":   len(patient_data or []),
            "n_series":     len(series_data or []),
            "modalities":   modalities or [],
            "sample_series": (series_data or [])[:5],
        }

    def save_download_instructions(self):
        """Saves plain-language instructions for downloading imaging data."""
        instructions = {
            "note": "DICOM images require NBIA Data Retriever (free download from TCIA).",
            "steps": [
                "1. Install NBIA Data Retriever: https://wiki.cancerimagingarchive.net/display/NBIA/Downloading+TCIA+Images",
                "2. Search for collection at https://www.cancerimagingarchive.net/",
                "3. Click 'Download' to get a .tcia manifest file",
                "4. Open manifest in NBIA Data Retriever to download DICOM files",
                "5. Use pydicom to read DICOM files in Python"
            ],
            "python_example": (
                "import pydicom\n"
                "ds = pydicom.dcmread('path/to/file.dcm')\n"
                "pixel_array = ds.pixel_array  # numpy array\n"
                "print(ds.Modality, ds.StudyDescription)"
            ),
            "collections": BREAST_COLLECTIONS
        }
        self.save(instructions, "tcia_download_instructions.json")

    def collect(self, **kwargs):
        print("\n[TCIA] Fetching imaging collection metadata")

        results = []
        for coll in BREAST_COLLECTIONS:
            coll_id = coll["id"]
            print(f"  {coll_id}...", end=" ", flush=True)
            meta = self.get_collection_metadata(coll_id)
            meta.update(coll)
            results.append(meta)
            print(f"patients={meta['n_patients']} series={meta['n_series']}")

        self.save(results, "tcia_breast_collections.json")
        self.save_download_instructions()

        # Also check for any new collections via API
        print("\n  Checking for additional breast collections...")
        api_breast = self.get_breast_collections()
        api_ids    = [str(c) for c in api_breast]
        known_ids  = [c["id"] for c in BREAST_COLLECTIONS]
        new_colls  = [c for c in api_ids if c not in known_ids]
        if new_colls:
            print(f"  Found {len(new_colls)} additional collections: {new_colls}")
            self.save(new_colls, "tcia_additional_collections.json")

        return results
