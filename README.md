# Multi-Source Candidate Data Transformer

A production-quality Python pipeline to ingest candidate profiles from multiple heterogeneous sources (structured ATS JSON and unstructured Resume PDF), normalize the data, merge conflicts using deterministic confidence scores, track field-level provenance, validate the output schema, and format custom configurations on the fly.

---

## Architecture Overview

```
[Resume PDF] ──► [PdfParser] ──┐
                               ├──► [RawCandidate] ──► [ProfileMerger] ──► [CanonicalCandidate]
[ATS JSON]   ──► [JsonParser]  ──┘          ▲                  │
                                            │                  ▼
                                     [Normalizers]      [SchemaProjector]
                                                               │
                                                               ▼
[output/candidate.json] ◄── [OutputValidator] ◄────────────────┘
```

1. **Ingestion**: Raw files are ingested by format-specific parsers. Unstructured PDF resumes are parsed heuristically using `pdfplumber` and regular expressions. ATS JSON structures are mapped directly.
2. **Normalization**: Individual field elements (phone numbers, dates, skills, country codes) are normalized to their canonical forms (E.164, YYYY-MM, canonical skill names, ISO-3166 Alpha-2).
3. **Merging**: Standardized records are merged field-by-field. Conflicting entries resolve using confidence scoring. Elements present in multiple sources receive confidence boosts (to `1.0`), and their source histories are tracked.
4. **Projection**: Translates the internal canonical representation into client-specified JSON formats (handling nested path remappings, field selection, and metadata toggles) using runtime configs.
5. **Validation**: Validates the output through micro-Pydantic schemas. Validation failures are captured, logging warnings and falling back to `null` to ensure crash-free execution.

---

## Installation & Dependencies

Ensure you have Python 3.10+ installed.

1. Clone or copy the project folder.
2. Install the required dependencies:
   ```bash
   pip install pdfplumber pydantic phonenumbers pytest
   ```

---

## How to Run

Run the pipeline using the command line interface:

```bash
python main.py \
    --resume input/resume.pdf \
    --ats input/ats.json \
    --config config/default.json \
    --output output/candidate.json
```

---

## Configuration Schema

The pipeline is configured using a runtime JSON file (e.g. `config/default.json`).

### Options:
- **`fields`**: Configures selection, paths, and renaming.
  - `path`: The source field in the canonical candidate profile (`name`, `email`, `phone`, `skills`, `education`, `experience`, `country`).
  - `rename`: Target key. Supports nested path mapping using dot notation (e.g. `"personal_info.full_name"`).
- **`include_confidence`**: `true`/`false`. Toggles inclusion of confidence values.
- **`include_provenance`**: `true`/`false`. Toggles inclusion of source provenance records.
- **`missing_field_policy`**: Behavior when a configured field is missing:
  - `"null"`: Output key with value `null`.
  - `"omit"`: Exclude the key from the output entirely.
  - `"error"`: Raise an exception.

---

## Examples

### Input Examples

#### ATS JSON (`input/ats.json`)
```json
{
  "first_name": "Jane",
  "last_name": "Doe",
  "email": "jane.doe@example.com",
  "phone": "+1 (555) 019-9988",
  "country": "United States",
  "skills": ["Python", "JS"],
  "education_history": [
    {
      "school": "Stanford University",
      "degree_name": "B.S.",
      "major": "Computer Science",
      "start": "2018-09",
      "end": "2022-06"
    }
  ]
}
```

#### Resume PDF (`input/resume.pdf`)
A PDF resume containing:
- Name: Jane Doe
- Email: jane.doe@example.com
- Phone: +1 555 019 9988
- Skills: Python, ReactJS
- Education: Stanford University, CS, B.S., 2018 - 2022

### Output Example (`output/candidate.json`)
Using default config:
```json
{
  "full_name": {
    "value": "Jane Doe",
    "confidence": 1.0,
    "provenance": [
      {
        "field": "name",
        "source": "resume",
        "extraction_method": "pdf_structure"
      },
      {
        "field": "name",
        "source": "ats",
        "extraction_method": "ats_json"
      }
    ]
  },
  "email_address": {
    "value": "jane.doe@example.com",
    "confidence": 1.0,
    "provenance": [
      {
        "field": "email",
        "source": "resume",
        "extraction_method": "regex"
      },
      {
        "field": "email",
        "source": "ats",
        "extraction_method": "ats_json"
      }
    ]
  },
  "phone_number": {
    "value": "+15550199988",
    "confidence": 1.0,
    "provenance": [
      {
        "field": "phone",
        "source": "resume",
        "extraction_method": "regex"
      },
      {
        "field": "phone",
        "source": "ats",
        "extraction_method": "ats_json"
      }
    ]
  },
  "skills": [
    {
      "value": "Python",
      "confidence": 1.0,
      "provenance": [
        {
          "field": "skills",
          "source": "resume",
          "extraction_method": "pdf_structure"
        },
        {
          "field": "skills",
          "source": "ats",
          "extraction_method": "ats_json"
        }
      ]
    },
    {
      "value": "JavaScript",
      "confidence": 0.9,
      "provenance": [
        {
          "field": "skills",
          "source": "ats",
          "extraction_method": "ats_json"
        }
      ]
    },
    {
      "value": "React",
      "confidence": 0.8,
      "provenance": [
        {
          "field": "skills",
          "source": "resume",
          "extraction_method": "pdf_structure"
        }
      ]
    }
  ],
  "education_history": [
    {
      "value": {
        "institution": "Stanford University",
        "degree": "B.S.",
        "field_of_study": "Computer Science",
        "start_date": "2018-09",
        "end_date": "2022-06"
      },
      "confidence": 1.0,
      "provenance": [
        {
          "field": "education",
          "source": "resume",
          "extraction_method": "pdf_structure"
        },
        {
          "field": "education",
          "source": "ats",
          "extraction_method": "ats_json"
        }
      ]
    }
  ],
  "work_history": null,
  "country_code": {
    "value": "US",
    "confidence": 1.0,
    "provenance": [
      {
        "field": "country",
        "source": "resume",
        "extraction_method": "pdf_structure"
      },
      {
        "field": "country",
        "source": "ats",
        "extraction_method": "ats_json"
      }
    ]
  },
  "overall_confidence": 1.0
}
```

---

## Assumptions
1. **Source Reliability**: ATS inputs are considered explicitly structured and verified, hence they start with a higher baseline confidence (`0.9`). PDF parsing relies on regex and positional heuristic cues, starting at `0.8` (structure) and `0.6` (heuristic fields like phone/email).
2. **Matching Criteria**: Education records match if the institution name overlaps and degree names start with the same letter. Experience records match if normalized company names (without suffixes like "Inc.", "Corp.") match.
3. **Date Resolution**: Hand-written date segments are parsed to YYYY-MM. If only a year is available, it defaults to YYYY-01. "Present" / "Current" are preserved for ongoing engagements.

---

## Future Improvements
- **Semantic Entity Matching**: Replace token/regex matching for company names and education with vector embeddings or custom string distance weights (e.g. Jaro-Winkler).
- **Expanded PDF Layout Support**: Support multi-column PDFs by analyzing bounding boxes (PDF coordinates) instead of raw text line splits.
- **Dynamic Normalizer Mappings**: Move normalization catalogs (such as canonical skills or country maps) into external files or database lookups rather than inline maps.
