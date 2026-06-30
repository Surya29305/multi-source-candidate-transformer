# System Design: Multi-Source Candidate Data Transformer

This document details the architectural layout, pipeline processing steps, confidence policies, validation schema, edge-case handlings, and design tradeoffs of the Multi-Source Candidate Data Transformer.

---

## 1. Core Pipeline Workflow

The ingestion pipeline executes sequentially:

```
[Resume PDF] ──► PdfParser ──┐
                             ├──► Raw Profiles ──► Normalizers ──► Merger ──► Canonical ──► Projector ──► Validator ──► Output JSON
[ATS JSON]   ──► JsonParser ─┘
```

1. **Extraction (Parsers)**: Parses inputs into an un-normalized `RawCandidate` model.
2. **Standardization (Normalizers)**: Standardizes values (phone, dates, skills, country codes).
3. **Reconciliation (Merger)**: Resolves conflicts using a rule-based merging algorithm, calculating field confidences and tracking provenance histories.
4. **Formatting (Projector)**: Remaps schemas, selects/renames keys, and toggles metadata visibility according to a client JSON configuration.
5. **Quality Control (Validator)**: Validates target types via Pydantic, transforming invalid values to `null` to avoid crashes.

---

## 2. Shared Models & Architecture

We employ a **Clean Architecture** layout. Shared models are located under `models/`:
- **`RawCandidate`**: Structured format representing the parsed content from individual sources prior to normalization.
- **`FieldValue[T]`**: Generic container wrapping values with `confidence` and `provenance` metadata.
- **`CanonicalCandidate`**: The unified target domain profile composed of `FieldValue` properties.

By keeping `RawCandidate` separate from `CanonicalCandidate`, parsing rules remain decoupled from merge policies.

---

## 3. Normalization Strategies

Standardization happens in the normalizer layer:
- **Phone Numbers**: Normalizes phone strings using `phonenumbers` to the international E.164 standard. It falls back to `is_possible_number` to accept fictional test numbers.
- **Dates**: Resolves text dates (e.g. "June 2021" or "2021/06") to `YYYY-MM`. It defaults missing month segments to `-01` and preserves the "Present" or "Current" keywords for active positions.
- **Skills**: Performs case-insensitive matching against a canonical skill dictionary. It replaces variations like `ReactJS` or `JS` with their official terms (`React`, `JavaScript`).
- **Country Codes**: Maps names (e.g., `United States` or `USA`) to 2-letter ISO-3166 Alpha-2 codes.

---

## 4. Conflict Resolution & Merging

When merging duplicate attributes, the merger resolves conflicts as follows:
- **Single-Value Fields (Name, Email, Phone, Country)**: Selects the value with the highest confidence. If a field is present in both sources, the merged confidence is boosted to `1.0`, and both source provenances are combined.
- **Skill Deduplication**: Matches skill strings case-insensitively. Skills present in both sources are deduplicated, boosted to `1.0` confidence, and both sources are recorded in the provenance list.
- **Education matching**: Compares school names (ignoring keywords like "University", "College") and degrees (comparing the starting letter, e.g. "B" matches "B.S." and "Bachelor"). Matches are merged, filling empty values from the lower-confidence source.
- **Experience matching**: Standardizes company names (stripping legal suffixes like "Inc.", "Corp.") and matches them. Matches are merged, retaining the higher-confidence details and combining dates.

---

## 5. Confidence & Provenance Model

- **Baseline Confidences**:
  - ATS Ingest: `0.9` (Explicit structure)
  - Resume Ingest (Direct structure): `0.8` (Positional details like education/experience)
  - Resume Ingest (Heuristics): `0.6` (Regex-parsed email/phone)
  - Present in both: Promoted to `1.0`
- **Provenance Track**: Every `FieldValue` maintains a list of `Provenance` items:
  ```json
  {"field": "email", "source": "resume", "extraction_method": "regex"}
  ```
  During merges, provenance lists are appended together.

---

## 6. Edge Cases & Fail-Safe Policies

- **Missing Fields**: Handled by the Projector using a configurable `missing_field_policy`:
  - `null`: Keys are written as `null` in the output dictionary.
  - `omit`: Keys are excluded from the output.
  - `error`: Throws a `ValueError` immediately.
- **Malformed Formats (Safe-Null Fallback)**: If a projected email, phone, or country code is malformed, Pydantic validation catches the error, logs a warning, and converts the value to `null` instead of crashing. If metadata is enabled, it sets `value: null` but preserves the confidence and provenance wrapper.
- **Single-Source Executions**: If only a resume or only an ATS file is supplied, the merger converts the input to a canonical profile without merging, retaining the original confidences.

---

## 7. Tradeoffs & Decisions

- **Rule-Based Parsing vs. Semantic ML**: We use regex and token heuristic parsing instead of LLMs. *Tradeoff*: Faster, cheaper, deterministic execution, but susceptible to highly irregular resume formats.
- **Granular vs. Block-Level Provenance**: Education and Experience items are tracked as unified blocks (e.g., an entire education item has one confidence/provenance), rather than tracking provenance for individual text strings (like major or degree). *Tradeoff*: Prevents schema bloating while still maintaining robust provenance tracking.
- **Post-Projection Validation**: Pydantic validation runs *after* schema projection, allowing type checking on the final client-bound JSON payload. It decodes the config to match renamed keys. *Tradeoff*: High flexibility but requires lookup parsing during validation.
