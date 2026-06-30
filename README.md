# Multi-Source Candidate Data Transformer

A production-quality Python pipeline to ingest candidate profiles from multiple heterogeneous sources (structured ATS JSON, structured Recruiter CSV, unstructured Resume PDF, and unstructured LinkedIn Profile text), normalize the data, merge conflicts using deterministic confidence scores, track field-level provenance, validate the output schema, and format custom configurations on the fly.

---

## 🚀 Quick Start (5-Minute Run Guide)

### 1. Clone Repository & Navigate
```bash
git clone <repository_url>
cd Eightfold_assessment
```

### 2. Install Dependencies
```bash
pip install pdfplumber pydantic phonenumbers pytest
```

### 3. Run the Complete Pipeline (All 4 Sources + Default Config)
```bash
python main.py \
  --ats input/ats.json \
  --csv input/recruiter.csv \
  --resume input/resume.pdf \
  --linkedin input/linkedin.txt \
  --config config/default.json \
  --output output/all_four.json
```

### 4. Run with a Single Source (e.g. Recruiter CSV Only)
```bash
python main.py --csv input/recruiter.csv --output output/only_csv.json
```

### 5. Run with Custom Nested Schema Projection
```bash
python main.py \
  --ats input/ats.json \
  --csv input/recruiter.csv \
  --resume input/resume.pdf \
  --linkedin input/linkedin.txt \
  --config config/custom.json \
  --output output/all_four_custom.json
```

### 6. Run Test Suite
```bash
python -m pytest tests/
```

### 7. Interactive Setup Wizard Mode
Alternatively, configure and run the entire pipeline step-by-step:
```bash
python main.py -i
```

---

## 1. Project Features

- **Multi-Source Ingestion**: Ingest data from ATS JSON, Recruiter CSV, Resume PDF, and LinkedIn TXT files.
- **Robust Schema Normalization**: Standardizes emails, phones (E.164), country codes (ISO-3166-1 alpha-2), links, skills, and timelines.
- **Deterministic Merger**: Combines profiles based on deterministic priority orders (`ATS > CSV > Resume > LinkedIn`) with explicit base confidence scores and conflict penalties.
- **Confidence Tracking**: Calculates overall profile confidences using deterministic strategies.
- **Dynamic Configurable Projection**: Custom configurations allow remapping schemas dynamically (nested path routing, field filtering, dropping confidence/provenance fields) without rewriting backend code.
- **Safety Validation**: Micro-Pydantic models evaluate generated output fields and construct validation reports detailing field-level status messages.
- **Wizard Interactive CLI**: Friendly step-by-step setup mode.

---

## 2. Directory Structure

```text
Eightfold_assessment/
├── config/
│   ├── default.json            # Flat schema projection mapping with confidence & provenance
│   └── custom.json             # Nested schema projection mapping omitting metadata fields
├── input/
│   ├── ats.json                # Sample ATS source file
│   ├── recruiter.csv           # Sample Recruiter CSV source file
│   ├── resume.pdf              # Sample Resume PDF source file
│   └── linkedin.txt            # Sample LinkedIn text export file
├── merger/
│   └── profile_merger.py       # Core deduplication, priority resolution, and merging logic
├── models/
│   ├── raw.py                  # Pydantic schemas representing unmerged source inputs
│   └── canonical.py            # Pydantic schemas representing the unified candidate model
├── normalizers/
│   ├── country.py              # ISO-3166-1 alpha-2 mapping utilities
│   ├── date.py                 # Time and date segment formatting logic
│   ├── phone.py                # Phone E.164 normalizers
│   ├── skill.py                # Technical skill normalizers
│   └── links.py                # URL normalizers
├── parsers/
│   ├── base.py                 # Abstract Base Parser class
│   ├── json_parser.py          # ATS JSON parser
│   ├── csv_parser.py           # Recruiter CSV parser
│   ├── pdf_parser.py           # PDF resume parser
│   └── linkedin_parser.py      # LinkedIn txt parser (inherits from PdfParser)
├── projector/
│   └── schema_projector.py     # Runtime custom schema layout projector
├── validator/
│   └── output_validator.py     # Micro-validators & validation reporting
├── output/                     # Location where output files are generated
├── tests/                      # Pytest test suites
└── main.py                     # CLI Entrypoint & Setup Wizard
```

---

## 3. Installation & Dependencies

Make sure you have Python 3.10+ installed.

1. Clone or copy the project folder.
2. Install the required dependencies:
   ```bash
   pip install pdfplumber pydantic phonenumbers pytest
   ```

---

## 4. How to Run (Usability Guide)

The transformer can be run in two ways: **Interactive Setup Wizard** or **CLI Command Mode**.

### Option A: Interactive Setup Wizard (Highly Recommended for First-Time Users)
Launch the wizard to be guided step-by-step through configuring your inputs, projection configurations, and output destination:
```bash
python main.py -i
```
*Tip: Simply press ENTER during input questions to skip sources you don't wish to supply.*

### Option B: CLI Command Mode (For Automation & Scripting)
Supply all inputs directly via flags. Output paths are fully configurable via the `--output` flag.

**Example 1: Merge All Four Sources (ATS + CSV + Resume + LinkedIn)**
```bash
python main.py \
  --ats input/ats.json \
  --csv input/recruiter.csv \
  --resume input/resume.pdf \
  --linkedin input/linkedin.txt \
  --config config/default.json \
  --output output/all_four.json
```

**Example 2: Merge Only Two Sources (CSV + Resume)**
```bash
python main.py \
  --csv input/recruiter.csv \
  --resume input/resume.pdf \
  --config config/default.json \
  --output output/partial_sources.json
```

**Example 3: Generate Custom Nested Projection Output**
```bash
python main.py \
  --ats input/ats.json \
  --csv input/recruiter.csv \
  --resume input/resume.pdf \
  --linkedin input/linkedin.txt \
  --config config/custom.json \
  --output output/all_four_custom.json
```

---

## 5. Ingestion & Merging Strategy

### Confidence Scoring System
Confidence starts with the reliability of the source format:
- **ATS**: `0.90` (Structured, verified system of record)
- **Recruiter CSV**: `0.85` (Structured, recruiter upload)
- **Resume (Direct)**: `0.80` / **Resume (Heuristic)**: `0.60` (Unstructured text)
- **LinkedIn (Direct)**: `0.80` / **LinkedIn (Heuristic)**: `0.60` (Unstructured text)

- **Conflicting Overlaps**: Resolved deterministically by prioritizing inputs: `ATS > CSV > Resume > LinkedIn`. The selected value gets a conflict penalty of `-0.1` on its highest confidence score.
- **Identical Overlaps**: If a field matches identically across multiple sources, its confidence is boosted to `1.0` and all sources are tracked in its provenance.

---

## 6. Output Configurator (Default vs Custom Projection)

By changing the configuration path in `--config`, you alter the final schema output structure dynamically:
- **`config/default.json`**: Projects flat structures retaining the full provenance and confidence metrics per field.
- **`config/custom.json`**: Remaps fields into nested groups (e.g. `personal.residence`, `contact.socials`), omits confidence and provenance values to compress payload size, and ignores missing values (`omit` policy).

---

## 7. Troubleshooting

- **Missing Input Files Error**: The CLI expects at least one source file. Ensure the file paths are correctly spelled or run `python main.py -i` to verify paths.
- **Dependency Import Error**: Run `pip install pdfplumber pydantic phonenumbers pytest` to make sure all modules are available in your python environment.
- **PDF Parser Warning**: Some multi-column PDFs may not read in exact layout order. We handle this by splitting sections dynamically based on header boundaries.
