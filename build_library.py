"""
build_library.py
================
Downloads and saves data from all authoritative breast cancer sources.

Run order matters — SEER and FDA have no dependencies.
cBioPortal is large. TCIA is metadata only (images require separate download).

Usage:
  python build_library.py                    # run all collectors
  python build_library.py --only seer fda   # run specific collectors
  python build_library.py --skip tcia       # skip large/slow collectors

Environment variables (optional):
  ONCOKB_TOKEN    — OncoKB API token (free at oncokb.org)
  SEER_API_KEY    — SEER API key (free at seer.cancer.gov)
  NCBI_API_KEY    — NCBI API key (free at ncbi.nlm.nih.gov) — 10x rate limit
"""

import argparse
import json
import os
import time
from pathlib import Path

from collectors import (
    SEERCollector,
    FDACollector,
    OncoKBCollector,
    CBioPortalCollector,
    PubMedCollector,
    TCIACollector,
)

BASE_DIR = Path(__file__).parent

COLLECTORS = {
    "seer":        (SEERCollector,       {"output_dir": str(BASE_DIR / "data/clinical")}),
    "fda":         (FDACollector,        {"output_dir": str(BASE_DIR / "data/medications")}),
    "oncokb":      (OncoKBCollector,     {"output_dir": str(BASE_DIR / "data/biomarkers")}),
    "cbioportal":  (CBioPortalCollector, {"output_dir": str(BASE_DIR / "data/genomic")}),
    "pubmed":      (PubMedCollector,     {"output_dir": str(BASE_DIR / "data/literature")}),
    "tcia":        (TCIACollector,       {"output_dir": str(BASE_DIR / "data/imaging")}),
}

# Estimated run times and notes
COLLECTOR_INFO = {
    "seer":       {"time": "< 1 min",  "auth": "none",             "note": "Curated static data. No API needed."},
    "fda":        {"time": "2-5 min",  "auth": "none",             "note": "OpenFDA API. No registration."},
    "oncokb":     {"time": "3-5 min",  "auth": "ONCOKB_TOKEN",     "note": "Free registration at oncokb.org"},
    "cbioportal": {"time": "10-20 min","auth": "none",             "note": "Large dataset. Fetches TCGA + METABRIC metadata."},
    "pubmed":     {"time": "3-5 min",  "auth": "NCBI_API_KEY opt", "note": "Free. Optional key for higher rate limit."},
    "tcia":       {"time": "2-3 min",  "auth": "none",             "note": "Metadata only. Images need NBIA Data Retriever."},
}


def print_summary():
    print("\n" + "=" * 70)
    print("BREAST CANCER DATA LIBRARY — SOURCE CATALOG")
    print("=" * 70)
    print(f"  {'Collector':<14} {'Est. Time':<12} {'Auth Required':<20} {'Notes'}")
    print("  " + "-" * 68)
    for name, info in COLLECTOR_INFO.items():
        print(f"  {name:<14} {info['time']:<12} {info['auth']:<20} {info['note']}")
    print("=" * 70)


def run_collector(name: str, cls, kwargs: dict) -> bool:
    print(f"\n{'='*60}")
    print(f"COLLECTING: {name.upper()}")
    print(f"{'='*60}")
    t0 = time.time()
    try:
        collector = cls(**kwargs)
        collector.collect()
        elapsed = time.time() - t0
        print(f"\n[{name}] Done in {elapsed:.1f}s")
        return True
    except Exception as e:
        print(f"\n[{name}] FAILED: {e}")
        import traceback; traceback.print_exc()
        return False


def build_manifest(base_dir: Path):
    """Creates a manifest of all downloaded files."""
    manifest = {}
    for category in ("clinical","genomic","imaging","medications","biomarkers","literature","ontologies"):
        cat_dir = base_dir / "data" / category
        if cat_dir.exists():
            files = list(cat_dir.glob("*.json"))
            manifest[category] = [
                {"file": f.name, "size_kb": round(f.stat().st_size / 1024, 1)}
                for f in files
            ]
    path = base_dir / "data" / "manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved -> {path}")
    total_files = sum(len(v) for v in manifest.values())
    print(f"Total files collected: {total_files}")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Build breast cancer data library")
    parser.add_argument("--only", nargs="+", choices=list(COLLECTORS.keys()),
                        help="Run only these collectors")
    parser.add_argument("--skip", nargs="+", choices=list(COLLECTORS.keys()),
                        help="Skip these collectors")
    parser.add_argument("--list", action="store_true",
                        help="List all collectors and exit")
    args = parser.parse_args()

    print_summary()

    if args.list:
        return

    to_run = list(COLLECTORS.keys())
    if args.only:
        to_run = [c for c in to_run if c in args.only]
    if args.skip:
        to_run = [c for c in to_run if c not in args.skip]

    print(f"\nRunning collectors: {to_run}")

    results = {}
    for name in to_run:
        cls, kwargs = COLLECTORS[name]
        results[name] = run_collector(name, cls, kwargs)

    print("\n" + "=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)
    for name, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  {name:<14} {status}")

    build_manifest(BASE_DIR)


if __name__ == "__main__":
    main()
