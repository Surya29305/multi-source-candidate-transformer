import json
from pathlib import Path
from models.raw import RawCandidate, EducationRaw, ExperienceRaw
from parsers.base import BaseParser

class JsonParser(BaseParser):
    def parse(self, file_path: str) -> RawCandidate:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"ATS JSON file not found at: {file_path}")
            
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Resolve full candidate name
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        name = data.get("name")
        if not name and (first_name or last_name):
            name = f"{first_name} {last_name}".strip()
            
        email = data.get("email") or data.get("email_address")
        phone = data.get("phone") or data.get("phone_number")
        country = data.get("country") or data.get("country_code")
        
        # Skills
        skills = data.get("skills") or data.get("skills_list") or []
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
            
        # Education History
        education = []
        edu_list = data.get("education") or data.get("education_history") or []
        for edu in edu_list:
            education.append(EducationRaw(
                institution=edu.get("school") or edu.get("institution") or edu.get("university"),
                degree=edu.get("degree") or edu.get("degree_name"),
                field_of_study=edu.get("field_of_study") or edu.get("major") or edu.get("study_field"),
                start_date=edu.get("start_date") or edu.get("start") or edu.get("start_year"),
                end_date=edu.get("end_date") or edu.get("end") or edu.get("end_year"),
            ))
            
        # Work History
        experience = []
        exp_list = data.get("experience") or data.get("work_history") or data.get("employment") or []
        for exp in exp_list:
            experience.append(ExperienceRaw(
                company=exp.get("company") or exp.get("employer") or exp.get("organization"),
                role=exp.get("role") or exp.get("job_title") or exp.get("title"),
                start_date=exp.get("start_date") or exp.get("start") or exp.get("start_year"),
                end_date=exp.get("end_date") or exp.get("end") or exp.get("end_year"),
                location=exp.get("location") or exp.get("office_location") or exp.get("city"),
            ))
            
        return RawCandidate(
            name=name or None,
            email=email or None,
            phone=phone or None,
            skills=skills,
            education=education,
            experience=experience,
            country=country or None,
        )
