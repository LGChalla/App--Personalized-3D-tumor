# App — Personalized 3D Tumor

*Upload your pathology report. See your tumor in 3D. Understand your odds. Built for patients, starting with breast cancer.*

---

A patient-facing tool that takes what is written in clinical notes and lab results — staging, receptor status, tumor location, lymph node involvement — and turns it into something a person can actually see and interact with. A 3D body model showing where the tumor is. A survival timeline that updates when you change your treatment options. Plain language throughout.

Built first for one person. Designed to scale to every breast cancer subtype, then beyond.

---

## What It Does

**Upload** — Drop in a pathology report, lab result, or clinical note (PDF or text). The app parses it using Claude API and extracts tumor location, size, stage, receptor status (ER/PR/HER2/BRCA), lymph node count, and histology.

**Visualize** — A rotating 3D torso model places the tumor at the extracted coordinates — size-accurate, colour-coded by receptor subtype, with lymph node markers if involved.

**Explore** — Adjust sliders for age, treatment choice (surgery type, chemotherapy regimen, hormone therapy, immunotherapy), BRCA status, and Ki-67. The survival timeline updates in real time.

**Understand** — 5-year and 10-year survival curves with confidence bands. Treatment-specific benefit shown as "what this adds." Presented as a road ahead, not a verdict.

---

## Data Library

All survival statistics, biomarker data, drug information, and clinical knowledge come from primary authoritative sources. No estimates, no secondary summaries.

| Category | Source | Authority |
|----------|--------|-----------|
| Survival by stage/subtype | SEER StatFacts, NCI | Highest |
| Individualized survival | PREDICT v3 (Cambridge/NHS) | Highest |
| Biomarker → drug actionability | OncoKB (MSK) | Highest |
| Drug labels and dosing | FDA OpenFDA / DailyMed | Highest |
| Genomic mutation landscape | TCGA-BRCA via cBioPortal | Highest |
| BRCA1/2 variant classification | BRCA Exchange (GA4GH) | Highest |
| Clinical guidelines | NCCN, ASCO, ESMO | Highest |
| Treatment benefit estimates | EBCTCG meta-analyses | Highest |
| Imaging datasets | TCIA (CBIS-DDSM, Duke MRI) | High |
| Literature | PubMed Entrez API | Highest |

Full source catalog with URLs and API endpoints: `data/sources.json`

---

## Repository Structure

```
App--Personalized-3D-tumor/
├── collectors/              API clients for each data source
│   ├── seer.py              SEER survival statistics
│   ├── fda.py               FDA drug labels (OpenFDA)
│   ├── oncokb.py            Biomarker-drug actionability
│   ├── cbioportal.py        TCGA genomic data
│   ├── pubmed.py            Literature by topic
│   └── tcia.py              Imaging collection metadata
├── data/
│   ├── sources.json         Master catalog of all trustable sources with URLs
│   ├── medications/         Breast cancer drug library (curated)
│   ├── clinical/            SEER survival tables, treatment benefit
│   ├── genomic/             cBioPortal data (populated on build)
│   ├── biomarkers/          OncoKB actionability (populated on build)
│   ├── literature/          PubMed abstracts by topic (populated on build)
│   └── imaging/             TCIA collection metadata
├── build_library.py         Downloads all data from source APIs
└── requirements.txt
```

---

## How to Run

### 1. Clone and install

```bash
git clone https://github.com/LGChalla/App--Personalized-3D-tumor.git
cd App--Personalized-3D-tumor
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
# Required for document parsing
export ANTHROPIC_API_KEY=your_key

# Optional — free registration unlocks higher-quality data
export ONCOKB_TOKEN=your_oncokb_token        # oncokb.org (free)
export NCBI_API_KEY=your_ncbi_key            # ncbi.nlm.nih.gov (free, 10x rate limit)
export SEER_API_KEY=your_seer_key            # seer.cancer.gov (free, for custom queries)
export BIOPORTAL_API_KEY=your_bioportal_key  # bioportal.bioontology.org (free)
```

### 3. Build the data library

```bash
# Start with no-auth sources (works immediately)
python build_library.py --only seer fda pubmed tcia

# Add biomarker data once ONCOKB_TOKEN is set
python build_library.py --only oncokb

# Full build (all sources)
python build_library.py
```

### 4. Verify the build

```bash
python -c "
import json
manifest = json.load(open('data/manifest.json'))
for cat, files in manifest.items():
    print(f'{cat}: {len(files)} files')
"
```

Expected output after full build:
```
clinical:     4 files   (SEER survival, treatment benefit, curve params)
medications:  2 files   (FDA labels, curated drug library)
biomarkers:   2 files   (OncoKB actionability, approved drugs)
genomic:      5 files   (cBioPortal TCGA, METABRIC metadata)
literature:   11 files  (PubMed abstracts by topic + index)
imaging:      2 files   (TCIA collection metadata, download instructions)
```

---

## How to Evaluate

### Clinical accuracy of survival statistics

The SEER survival tables baked into `data/clinical/seer_survival_by_stage.json` can be verified directly against the published source:

```
https://seer.cancer.gov/statfacts/html/breast.html
```

Cross-check: Stage I 5-year survival should be 99%, Stage IV 28%.

### PREDICT tool validation

The individualized survival curves are generated using the PREDICT v3 API:

```bash
# Test PREDICT API directly
curl "https://breast.predict.nhs.uk/api/predict/" \
  -H "Content-Type: application/json" \
  -d '{"age":52,"screen_detected":true,"size":22,"grade":2,
       "nodes_positive":0,"er_status":1,"her2_status":0,"ki67":15}'
```

PREDICT has been externally validated on UK, Netherlands, and Canadian cohorts (published in Breast Cancer Research, 2019). The API returns treatment-specific survival probabilities — compare returned values against published validation cohort results.

### Biomarker-drug actionability

OncoKB levels can be independently verified at `oncokb.org`. Level 1 means FDA-approved in breast cancer. Cross-check:
- PIK3CA mutation → Alpelisib + Fulvestrant (Level 1, SOLAR-1 trial)
- BRCA1/2 → Olaparib (Level 1, OlympiA trial)
- ERBB2 amplification → Trastuzumab (Level 1)

### Document extraction accuracy

Test the Claude extraction with a sample pathology report:

```python
from anthropic import Anthropic

client = Anthropic()
sample_note = """
Surgical pathology report. Right breast, 2 o'clock position, core biopsy.
Diagnosis: Invasive ductal carcinoma, grade 2. Tumor size: 1.8 cm.
ER: Positive (95%). PR: Positive (60%). HER2: Negative (IHC 1+).
Sentinel node: 0/3 positive. Ki-67: 18%.
"""

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=512,
    messages=[{
        "role": "user",
        "content": f"""Extract breast cancer staging from this note as JSON:
{sample_note}

Return: tumor_size_mm, stage, T, N, M, er_status, pr_status, her2_status,
ki67_percent, grade, location_clock, location_side, nodes_positive, nodes_total"""
    }]
)
print(response.content[0].text)
```

Expected extraction from the sample above:
```json
{
  "tumor_size_mm": 18,
  "er_status": "positive",
  "pr_status": "positive",
  "her2_status": "negative",
  "ki67_percent": 18,
  "grade": 2,
  "location_clock": 2,
  "location_side": "right",
  "nodes_positive": 0,
  "nodes_total": 3
}
```

---

## Validation Discussion

### What this is

A visualization and probability tool built on authoritative clinical data. The survival curves come from SEER (US population, 2013–2019) and PREDICT v3 (validated on 100,000+ patients across three countries). The biomarker-drug relationships come directly from OncoKB, which is an FDA-recognized knowledge base used in clinical decision support. The drug information comes from FDA prescribing labels.

### What this is not

This is not a diagnostic tool. It does not replace oncologist consultation. It does not account for individual factors that a treating physician would — comorbidities, organ function, performance status, patient preference, institutional protocols. The "what if I add this treatment" sliders show population-level benefit, not individual prediction.

### Survival curve limitations

SEER survival statistics are population averages. A patient who is younger, healthier, and treated at a high-volume center will do better than the average. A patient with multiple comorbidities may do worse. The PREDICT tool narrows this gap significantly — it takes individual tumor characteristics as inputs and was specifically built for individualized prediction — but it too has confidence intervals that widen for rarer subtypes and older patients.

SEER data lags by approximately 4–5 years. Survival statistics for HER2+ disease in particular have improved substantially since the widespread adoption of pertuzumab and T-DM1, meaning the SEER numbers shown may understate current outcomes for HER2+ patients.

### Imaging data

The TCIA collections (CBIS-DDSM, Duke MRI) are used for training the 3D tumor placement model, not for diagnosis. A tumor localized to the 2 o'clock position of the right breast in a clinical note will appear at the corresponding anatomical coordinate in the 3D viewer — this is visualization of extracted text, not analysis of the patient's actual imaging.

### What to validate before clinical use

Before this tool is used in any formal clinical or research context:
1. PREDICT API outputs should be compared to oncologist-provided survival estimates for 20+ cases
2. Document extraction accuracy should be tested on 50+ de-identified real reports across multiple institution formats
3. A clinician should review all biomarker-drug relationships shown at Level 2 and below (Level 1 is FDA-approved, directly verifiable)
4. Survival curves should be compared against the published PREDICT validation cohort results

---

*Laxmigayathri Challa · PhD, Information Science (Data Science) · University of North Texas*
*Not for clinical use. All survival estimates are population-level statistics from published sources.*
