import json
from pathlib import Path
from models.raw import RawCandidate, EducationRaw, ExperienceRaw, LocationRaw, LinksRaw
from parsers.base import BaseParser

class JsonParser(BaseParser):
    def parse(self, file_path: str) -> RawCandidate:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"ATS JSON file not found at: {file_path}")
            
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        name = data.get("name")
        if not name and (first_name or last_name):
            name = f"{first_name} {last_name}".strip()
            
        candidate_id = data.get("candidate_id") or data.get("id")
        if candidate_id is not None:
            candidate_id = str(candidate_id)
            
        # Emails
        emails = []
        raw_email = data.get("email") or data.get("email_address") or data.get("emails")
        if isinstance(raw_email, list):
            emails.extend([str(e) for e in raw_email if e])
        elif isinstance(raw_email, str):
            emails.append(raw_email)
            
        # Phones
        phones = []
        raw_phone = data.get("phone") or data.get("phone_number") or data.get("phones")
        if isinstance(raw_phone, list):
            phones.extend([str(p) for p in raw_phone if p])
        elif isinstance(raw_phone, str):
            phones.append(raw_phone)
            
        # Location
        location = LocationRaw(
            city=data.get("city"),
            region=data.get("region") or data.get("state"),
            country=data.get("country") or data.get("country_code")
        )
        if not any([location.city, location.region, location.country]):
            location = None
            
        # Links
        links_data = data.get("links", {})
        links = LinksRaw()
        if isinstance(links_data, dict):
            links.linkedin = links_data.get("linkedin")
            links.github = links_data.get("github")
            links.portfolio = links_data.get("portfolio")
            links.other = links_data.get("other", [])
            if not any([links.linkedin, links.github, links.portfolio, links.other]):
                links = None
        else:
            links = None
            
        headline = data.get("headline") or data.get("title")
        
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
            candidate_id=candidate_id,
            full_name=name or None,
            emails=emails,
            phones=phones,
            location=location,
            links=links,
            headline=headline or None,
            skills=skills,
            education=education,
            experience=experience
        )
