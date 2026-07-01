import argparse
import json
import logging
import sys
import io
from pathlib import Path
from typing import Optional, Dict

# ---------------------------------------------------------------------------
# Ensure UTF-8 output on Windows terminals (prevents UnicodeEncodeError)
# ---------------------------------------------------------------------------
if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from utils import setup_logger
from parsers import PdfParser, JsonParser, CsvParser, LinkedinParser
from merger import ProfileMerger
from projector import SchemaProjector
from validator import OutputValidator

logger = setup_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SAMPLE_FILES = {
    "ats": "input/ats.json",
    "csv": "input/recruiter.csv",
    "resume": "input/resume.pdf",
    "linkedin": "input/linkedin.txt",
}

HEADER_LINE = "=" * 60


def print_header():
    """Print the pipeline header banner."""
    print(f"\n{HEADER_LINE}")
    print("  Multi-Source Candidate Data Transformer")
    print(HEADER_LINE)


def print_section(title: str):
    """Print a section sub-header."""
    print(f"\n  [{title}]")
    print(f"  {'-' * (len(title) + 2)}")


# ---------------------------------------------------------------------------
# CLI Argument Parser
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Multi-Source Candidate Data Transformer — "
                    "Merge candidate profiles from ATS, CSV, Resume, "
                    "and LinkedIn into a single validated JSON profile.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py --ats input/ats.json --output output/result.json\n"
            "  python main.py --ats input/ats.json --csv input/recruiter.csv --resume input/resume.pdf --linkedin input/linkedin.txt\n"
            "  python main.py --config config/custom.json --ats input/ats.json --output output/nested.json\n"
            "  python main.py -i\n"
        ),
    )
    parser.add_argument(
        "--ats",
        type=str,
        default=None,
        help="Path to a structured Applicant Tracking System export (.json). "
             "Highest priority source (confidence: 0.90)."
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Path to a structured recruiter spreadsheet export (.csv). "
             "Second priority source (confidence: 0.85)."
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Path to an unstructured candidate resume (.pdf). "
             "Parsed via heuristic text extraction (confidence: 0.60-0.80)."
    )
    parser.add_argument(
        "--linkedin",
        type=str,
        default=None,
        help="Path to an unstructured LinkedIn profile exported as plain text (.txt). "
             "Lowest priority fallback source (confidence: 0.60-0.80)."
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/default.json",
        help="Path to the projection schema configuration (.json). "
             "Controls output field layout, metadata inclusion, and missing-field policy. "
             "Default: config/default.json"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output/candidate.json",
        help="Destination path for the generated merged candidate profile (.json). "
             "Parent directories are created automatically. "
             "Default: output/candidate.json"
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Launch interactive setup wizard. Prompts for each input file, "
             "configuration, and output path step by step."
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Interactive Mode
# ---------------------------------------------------------------------------
def run_interactive() -> Dict[str, Optional[str]]:
    """Prompt the user for each input file and configuration interactively."""
    print_section("Interactive Setup Wizard")
    print("  Enter file paths for each source. Press ENTER to skip.\n")

    ats = input("  ATS JSON path      (e.g. input/ats.json)       : ").strip()
    csv_file = input("  Recruiter CSV path (e.g. input/recruiter.csv)  : ").strip()
    resume = input("  Resume PDF path    (e.g. input/resume.pdf)      : ").strip()
    linkedin = input("  LinkedIn TXT path  (e.g. input/linkedin.txt)   : ").strip()

    print("\n  Projection Configuration:")
    print("    1. Default  — Flat schema, includes confidence & provenance")
    print("    2. Custom   — Nested schema, omits confidence & provenance")
    print("    3. Specify a custom config file path")
    choice = input("  Select [1/2/3] (Default: 1): ").strip()

    config = "config/default.json"
    if choice == "2":
        config = "config/custom.json"
    elif choice == "3":
        config = input("  Config file path: ").strip() or "config/default.json"

    output = input("\n  Output path (Default: output/candidate.json): ").strip() or "output/candidate.json"

    return {
        "ats": ats or None,
        "csv": csv_file or None,
        "resume": resume or None,
        "linkedin": linkedin or None,
        "config": config,
        "output": output,
    }


# ---------------------------------------------------------------------------
# Sample File Detection
# ---------------------------------------------------------------------------
def detect_sample_files() -> bool:
    """Check if the bundled sample input files exist."""
    return all(Path(p).exists() for p in SAMPLE_FILES.values())


def prompt_use_samples() -> bool:
    """Ask the user whether to run with the included sample files."""
    print("\n  No input arguments supplied.")
    print("  Sample input files were found in input/.")
    response = input("\n  Would you like to run with the sample files? [Y/n] ").strip().lower()
    return response in ("", "y", "yes")


# ---------------------------------------------------------------------------
# Pipeline Execution
# ---------------------------------------------------------------------------
def run_pipeline(ats_arg, csv_arg, resume_arg, linkedin_arg, config_arg, output_arg):
    """Execute the full transformation pipeline."""

    # ── Configuration ──────────────────────────────────────────────────
    print_section("Configuration")
    config_path = Path(config_arg)
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    print(f"  Config file : {config_path}")

    # ── Input Sources ──────────────────────────────────────────────────
    print_section("Input Sources")

    source_labels = {
        "ats": ("ATS JSON", ats_arg),
        "csv": ("Recruiter CSV", csv_arg),
        "resume": ("Resume PDF", resume_arg),
        "linkedin": ("LinkedIn TXT", linkedin_arg),
    }

    sources = {}
    parsers_map = {
        "ats": ("ATS JSON", JsonParser),
        "csv": ("Recruiter CSV", CsvParser),
        "resume": ("Resume PDF", PdfParser),
        "linkedin": ("LinkedIn TXT", LinkedinParser),
    }

    for key, (label, arg) in source_labels.items():
        if arg:
            path = Path(arg)
            if path.exists():
                parser_label, parser_cls = parsers_map[key]
                try:
                    raw = parser_cls().parse(str(path))
                    sources[key] = raw
                    name = raw.full_name or "Unknown"
                    print(f"  [+] {label:16s} : {path}  (Candidate: {name})")
                except Exception as e:
                    print(f"  [!] {label:16s} : PARSE ERROR — {e}")
            else:
                print(f"  [!] {label:16s} : File not found — {path}")
        else:
            print(f"  [ ] {label:16s} : Skipped (no file provided)")

    if not sources:
        logger.error("No sources were successfully parsed. Exiting.")
        sys.exit(1)

    # ── Pipeline Stages ────────────────────────────────────────────────
    print_section("Pipeline Stages")

    # Merge
    merger = ProfileMerger()
    canonical_profile = merger.merge(sources)
    print("  [+] Parsing        : Complete")
    print("  [+] Normalization  : Complete")
    print("  [+] Merge          : Complete")

    # Project
    projector = SchemaProjector()
    try:
        projected_data = projector.project(canonical_profile, config)
    except ValueError as e:
        logger.error(f"Projection failed: {e}")
        sys.exit(1)
    print("  [+] Projection     : Complete")

    # Validate
    validator = OutputValidator()
    validated_output = validator.validate(projected_data, config)
    print("  [+] Validation     : Complete")

    # ── Write Output ───────────────────────────────────────────────────
    output_path = Path(output_arg)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(validated_output, f, indent=2, ensure_ascii=False)

    # ── Output Summary ─────────────────────────────────────────────────
    print_section("Output")
    print(f"  File         : {output_path.resolve()}")

    overall_conf = validated_output.get("overall_confidence")
    if overall_conf is not None:
        print(f"  Confidence   : {overall_conf}")

    source_count = len(sources)
    print(f"  Sources used : {source_count}")

    print(f"\n{HEADER_LINE}")
    print("  Pipeline completed successfully.")
    print(HEADER_LINE)


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------
def main() -> None:
    print_header()
    args = parse_args()

    # ── Interactive mode ───────────────────────────────────────────────
    if args.interactive:
        wizard_args = run_interactive()
        ats_arg = wizard_args["ats"]
        csv_arg = wizard_args["csv"]
        resume_arg = wizard_args["resume"]
        linkedin_arg = wizard_args["linkedin"]
        config_arg = wizard_args["config"]
        output_arg = wizard_args["output"]

    # ── No-argument smart detection ────────────────────────────────────
    elif not args.ats and not args.csv and not args.resume and not args.linkedin:
        if detect_sample_files():
            if prompt_use_samples():
                ats_arg = SAMPLE_FILES["ats"]
                csv_arg = SAMPLE_FILES["csv"]
                resume_arg = SAMPLE_FILES["resume"]
                linkedin_arg = SAMPLE_FILES["linkedin"]
                config_arg = args.config
                output_arg = args.output
            else:
                # User declined samples — launch interactive mode
                wizard_args = run_interactive()
                ats_arg = wizard_args["ats"]
                csv_arg = wizard_args["csv"]
                resume_arg = wizard_args["resume"]
                linkedin_arg = wizard_args["linkedin"]
                config_arg = wizard_args["config"]
                output_arg = wizard_args["output"]
        else:
            # No sample files found — launch interactive mode
            print("\n  No input arguments supplied and no sample files found.")
            print("  Launching interactive setup wizard...")
            wizard_args = run_interactive()
            ats_arg = wizard_args["ats"]
            csv_arg = wizard_args["csv"]
            resume_arg = wizard_args["resume"]
            linkedin_arg = wizard_args["linkedin"]
            config_arg = wizard_args["config"]
            output_arg = wizard_args["output"]

    # ── Standard CLI mode ──────────────────────────────────────────────
    else:
        ats_arg = args.ats
        csv_arg = args.csv
        resume_arg = args.resume
        linkedin_arg = args.linkedin
        config_arg = args.config
        output_arg = args.output

    # Check that at least one data source is provided
    if not ats_arg and not csv_arg and not resume_arg and not linkedin_arg:
        logger.error("At least one data source is required (--ats, --csv, --resume, or --linkedin).")
        logger.info("Tip: Run with -i or --interactive for guided setup.")
        sys.exit(1)

    run_pipeline(ats_arg, csv_arg, resume_arg, linkedin_arg, config_arg, output_arg)


if __name__ == "__main__":
    main()
