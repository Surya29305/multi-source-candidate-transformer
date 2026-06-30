import argparse
import json
import logging
from pathlib import Path
from typing import Optional

from utils import setup_logger
from parsers import PdfParser, JsonParser, CsvParser, LinkedinParser
from merger import ProfileMerger
from projector import SchemaProjector
from validator import OutputValidator

logger = setup_logger()

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional, Dict

from utils import setup_logger
from parsers import PdfParser, JsonParser, CsvParser, LinkedinParser
from merger import ProfileMerger
from projector import SchemaProjector
from validator import OutputValidator

logger = setup_logger()

ASCII_BANNER = """
======================================================================
  ██████╗ ██████╗ ███╗   ██╗███████╗ ██████╗ ██████╗ ███╗   ███╗██╗██████╗ 
  ██╔══██╗██╔══██╗████╗  ██║██╔════╝██╔═══██╗██╔══██╗████╗ ████║██║██╔══██╗
  ██████╔╝██████╔╝██╔██╗ ██║█████╗  ██║   ██║██████╔╝██╔████╔██║██║██████╔╝
  ██╔═══╝ ██╔══██╗██║╚██╗██║██╔══╝  ██║   ██║██╔══██╗██║╚██╔╝██║██║██╔═══╝ 
  ██║     ██║  ██║██║ ╚████║███████╗╚██████╔╝██║  ██║██║ ╚═╝ ██║██║██║     
  ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝     
               Candidate Data Transformer Pipeline v1.2.0
======================================================================
"""

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Multi-Source Candidate Data Transformer CLI"
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Path to the unstructured candidate resume PDF"
    )
    parser.add_argument(
        "--ats",
        type=str,
        default=None,
        help="Path to the structured ATS candidate JSON"
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Path to the structured Recruiter CSV"
    )
    parser.add_argument(
        "--linkedin",
        type=str,
        default=None,
        help="Path to the unstructured LinkedIn Profile text"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/default.json",
        help="Path to the runtime projection JSON configuration"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output/candidate.json",
        help="Path to write the merged, canonicalized candidate profile"
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run the CLI in interactive setup wizard mode"
    )
    return parser.parse_args()

def run_interactive() -> Dict[str, Optional[str]]:
    print("\n--- Interactive Source Configuration Wizard ---")
    print("For each source file, press ENTER to skip if not available.\n")
    
    ats = input("1. Enter ATS JSON file path (e.g. input/ats.json): ").strip()
    csv_file = input("2. Enter Recruiter CSV file path (e.g. input/recruiter.csv): ").strip()
    resume = input("3. Enter Resume PDF file path (e.g. input/resume.pdf): ").strip()
    linkedin = input("4. Enter LinkedIn Profile text file path (e.g. input/linkedin.txt): ").strip()
    
    print("\nChoose Projection Configuration:")
    print("  1. Default Schema (Flat, include confidence & provenance)")
    print("  2. Custom Schema (Nested, omit confidence & provenance)")
    print("  3. Specify custom config JSON path")
    choice = input("Select [1-3] (Default: 1): ").strip()
    
    config = "config/default.json"
    if choice == "2":
        config = "config/custom.json"
    elif choice == "3":
        config = input("Enter configuration file path: ").strip() or "config/default.json"
        
    output = input("\nEnter Output Destination path (Default: output/candidate.json): ").strip() or "output/candidate.json"
    
    return {
        "ats": ats or None,
        "csv": csv_file or None,
        "resume": resume or None,
        "linkedin": linkedin or None,
        "config": config,
        "output": output
    }

def main() -> None:
    print(ASCII_BANNER)
    args = parse_args()
    
    # Check if running in wizard mode
    if args.interactive:
        wizard_args = run_interactive()
        ats_arg = wizard_args["ats"]
        csv_arg = wizard_args["csv"]
        resume_arg = wizard_args["resume"]
        linkedin_arg = wizard_args["linkedin"]
        config_arg = wizard_args["config"]
        output_arg = wizard_args["output"]
    else:
        ats_arg = args.ats
        csv_arg = args.csv
        resume_arg = args.resume
        linkedin_arg = args.linkedin
        config_arg = args.config
        output_arg = args.output
        
    # Check that at least one data source is provided
    if not resume_arg and not ats_arg and not csv_arg and not linkedin_arg:
        logger.error("[Error]: At least one data source (--resume, --ats, --csv, or --linkedin) must be provided.")
        if not args.interactive:
            logger.info("Tip: Run with -i or --interactive for a step-by-step setup wizard.")
        sys.exit(1)
        
    # 1. Load config
    config_path = Path(config_arg)
    if not config_path.exists():
        logger.error(f"[Error]: Configuration file not found at: {config_path}")
        sys.exit(1)
        
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    logger.info(f"⚙️  Loaded projection config from: {config_path}")

    sources = {}
    
    # 2. Parse ATS JSON if provided
    if ats_arg:
        ats_path = Path(ats_arg)
        if ats_path.exists():
            logger.info(f"📂 Parsing ATS JSON: {ats_path} ...")
            json_parser = JsonParser()
            try:
                ats_raw = json_parser.parse(str(ats_path))
                logger.info(f" ✅ Successfully parsed ATS details for: {ats_raw.full_name or 'Unknown'}")
                sources["ats"] = ats_raw
            except Exception as e:
                logger.error(f" ❌ Failed to parse ATS JSON: {e}")
        else:
            logger.warning(f" ⚠️ ATS JSON path does not exist: {ats_path}")
            
    # 3. Parse Recruiter CSV if provided
    if csv_arg:
        csv_path = Path(csv_arg)
        if csv_path.exists():
            logger.info(f"📂 Parsing Recruiter CSV: {csv_path} ...")
            csv_parser = CsvParser()
            try:
                csv_raw = csv_parser.parse(str(csv_path))
                logger.info(f" ✅ Successfully parsed Recruiter CSV for: {csv_raw.full_name or 'Unknown'}")
                sources["csv"] = csv_raw
            except Exception as e:
                logger.error(f" ❌ Failed to parse Recruiter CSV: {e}")
        else:
            logger.warning(f" ⚠️ Recruiter CSV path does not exist: {csv_path}")

    # 4. Parse Resume PDF if provided
    if resume_arg:
        resume_path = Path(resume_arg)
        if resume_path.exists():
            logger.info(f"📂 Parsing Resume PDF: {resume_path} ...")
            pdf_parser = PdfParser()
            try:
                resume_raw = pdf_parser.parse(str(resume_path))
                logger.info(f" ✅ Successfully parsed Resume for: {resume_raw.full_name or 'Unknown'}")
                sources["resume"] = resume_raw
            except Exception as e:
                logger.error(f" ❌ Failed to parse resume: {e}")
        else:
            logger.warning(f" ⚠️ Resume PDF path does not exist: {resume_path}")
            
    # 5. Parse LinkedIn text if provided
    if linkedin_arg:
        linkedin_path = Path(linkedin_arg)
        if linkedin_path.exists():
            logger.info(f"📂 Parsing LinkedIn Profile: {linkedin_path} ...")
            linkedin_parser = LinkedinParser()
            try:
                linkedin_raw = linkedin_parser.parse(str(linkedin_path))
                logger.info(f" ✅ Successfully parsed LinkedIn details for: {linkedin_raw.full_name or 'Unknown'}")
                sources["linkedin"] = linkedin_raw
            except Exception as e:
                logger.error(f" ❌ Failed to parse LinkedIn text: {e}")
        else:
            logger.warning(f" ⚠️ LinkedIn profile path does not exist: {linkedin_path}")
            
    # 6. Merge profiles
    if not sources:
        logger.error("[Error]: No sources were successfully parsed. Exiting pipeline.")
        sys.exit(1)
        
    logger.info("🔄 Merging candidate profiles & applying normalizers...")
    merger = ProfileMerger()
    canonical_profile = merger.merge(sources)
    
    # 7. Project according to schema config
    logger.info("📐 Projecting canonical profile into custom schema...")
    projector = SchemaProjector()
    try:
        projected_data = projector.project(canonical_profile, config)
    except ValueError as e:
        logger.error(f" ❌ Projector failed due to missing field policy: {e}")
        sys.exit(1)
        
    # 8. Validate output safely
    logger.info("🔍 Running output schema validator...")
    validator = OutputValidator()
    validated_output = validator.validate(projected_data, config)
    
    # 9. Write output
    output_path = Path(output_arg)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(validated_output, f, indent=2, ensure_ascii=False)
        
    print("\n" + "=" * 70)
    print(" 🎉 SUCCESS: Candidate Profile Transformed Successfully!")
    print(f" 📂 Generated JSON Location: {output_path.resolve()}")
    print("=" * 70)
    
    # Log summary info
    overall_conf = validated_output.get("overall_confidence")
    if overall_conf is not None:
        logger.info(f"Pipeline complete. Overall Profile Confidence: {overall_conf}")
    else:
        logger.info("Pipeline complete.")

if __name__ == "__main__":
    main()
