import csv
from typing import List, Optional
from models.raw import RawCandidate, EducationRaw, ExperienceRaw, LocationRaw, LinksRaw
from parsers.base import BaseParser

class CsvParser(BaseParser):
    def parse(self, file_path: str) -> RawCandidate:
        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                if not rows:
                    return RawCandidate()
                
                # Assume the first row represents the candidate
                raw_row = rows[0]
                row = {k.strip().lower(): v for k, v in raw_row.items() if k is not None}
                
                name = row.get("name", "").strip() or None
                
                email_raw = row.get("email", "").strip()
                emails = [e.strip() for e in email_raw.split(",") if e.strip()] if email_raw else []
                
                phone_raw = row.get("phone", "").strip()
                phones = [p.strip() for p in phone_raw.split(",") if p.strip()] if phone_raw else []
                
                skills_raw = row.get("skills", "").strip()
                skills = [s.strip() for s in skills_raw.split(",") if s.strip()] if skills_raw else []
                
                loc_raw = row.get("location", "").strip()
                location = None
                if loc_raw:
                    parts = [p.strip() for p in loc_raw.split(",")]
                    if len(parts) >= 2:
                        location = LocationRaw(city=parts[0], region=parts[1])
                    else:
                        location = LocationRaw(city=parts[0])
                
                experience = []
                current_company = row.get("current company", "").strip()
                current_role = row.get("current role", "").strip()
                if current_company or current_role:
                    experience.append(ExperienceRaw(
                        company=current_company or None,
                        role=current_role or None,
                        start_date="Present",
                        end_date="Present"
                    ))
                
                return RawCandidate(
                    full_name=name,
                    emails=emails,
                    phones=phones,
                    location=location,
                    skills=skills,
                    experience=experience
                )
        except Exception as e:
            raise RuntimeError(f"Failed to parse CSV file {file_path}: {e}")
