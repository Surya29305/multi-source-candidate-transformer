import argparse
import json
import logging
from pathlib import Path
from typing import Optional

from utils import setup_logger
from parsers import PdfParser, JsonParser
from merger import ProfileMerger
from projector import SchemaProjector
from validator import OutputValidator

logger = setup_logger()

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
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    logger.info("Initializing Multi-Source Candidate Data Transformer Pipeline...")
    
    # 1. Load config
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Configuration file not found at: {config_path}")
        return
        
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    logger.info(f"Loaded projection config from: {config_path}")
    
    # Check that at least one data source is provided
    if not args.resume and not args.ats:
        logger.error("Error: At least one data source (--resume or --ats) must be provided.")
        return

    resume_raw = None
    ats_raw = None
    
    # 2. Parse Resume PDF if provided
    if args.resume:
        resume_path = Path(args.resume)
        if resume_path.exists():
            logger.info(f"Parsing Resume PDF: {resume_path} ...")
            pdf_parser = PdfParser()
            try:
                resume_raw = pdf_parser.parse(str(resume_path))
                logger.info(f"Successfully parsed Resume for candidate: {resume_raw.name or 'Unknown'}")
            except Exception as e:
                logger.error(f"Failed to parse resume: {e}")
        else:
            logger.warning(f"Resume PDF path does not exist: {resume_path}")
            
    # 3. Parse ATS JSON if provided
    if args.ats:
        ats_path = Path(args.ats)
        if ats_path.exists():
            logger.info(f"Parsing ATS JSON: {ats_path} ...")
            json_parser = JsonParser()
            try:
                ats_raw = json_parser.parse(str(ats_path))
                logger.info(f"Successfully parsed ATS details for candidate: {ats_raw.name or 'Unknown'}")
            except Exception as e:
                logger.error(f"Failed to parse ATS JSON: {e}")
        else:
            logger.warning(f"ATS JSON path does not exist: {ats_path}")
            
    # 4. Merge profiles
    logger.info("Merging profiles & applying normalization rules...")
    merger = ProfileMerger()
    canonical_profile = merger.merge(resume_raw, ats_raw)
    
    # 5. Project according to schema config
    logger.info("Projecting canonical profile into target custom schema...")
    projector = SchemaProjector()
    try:
        projected_data = projector.project(canonical_profile, config)
    except ValueError as e:
        logger.error(f"Projector failed due to missing field policy: {e}")
        return
        
    # 6. Validate output safely
    logger.info("Running output schema validator...")
    validator = OutputValidator()
    validated_output = validator.validate(projected_data, config)
    
    # 7. Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(validated_output, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Successfully transformed profile saved to: {output_path}")
    
    # Log summary info
    overall_conf = validated_output.get("overall_confidence")
    if overall_conf is not None:
        logger.info(f"Pipeline complete. Overall Candidate Profile Confidence: {overall_conf}")
    else:
        logger.info("Pipeline complete.")

if __name__ == "__main__":
    main()
