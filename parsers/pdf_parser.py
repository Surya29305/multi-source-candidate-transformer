import re
from typing import List, Optional, Dict
import pdfplumber
from models.raw import RawCandidate, EducationRaw, ExperienceRaw
from parsers.base import BaseParser

KNOWN_SKILLS = [
    "Python", "Java", "JavaScript", "JS", "C++", "C#", "Go", "Golang", 
    "Rust", "SQL", "NoSQL", "Docker", "Kubernetes", "AWS", "Machine Learning", 
    "ML", "Deep Learning", "HTML", "CSS", "React", "ReactJS", "Node.js", 
    "Node", "TypeScript", "TS", "Git", "Linux"
]

class PdfParser(BaseParser):
    def parse(self, file_path: str) -> RawCandidate:
        text = self._extract_text(file_path)
        
        email = self._extract_email(text)
        phone = self._extract_phone(text)
        name = self._extract_name(text)
        country = self._extract_country(text)
        
        # Segment resume text into component sections
        sections = self._split_sections(text)
        
        # Skills might be concentrated in the skills section, or we scan globally
        skills = self._extract_skills(sections.get("skills", text))
        
        education = self._parse_education(sections.get("education", ""))
        experience = self._parse_experience(sections.get("experience", ""))
        
        return RawCandidate(
            name=name,
            email=email,
            phone=phone,
            skills=skills,
            education=education,
            experience=experience,
            country=country,
        )
        
    def _extract_text(self, file_path: str) -> str:
        try:
            with pdfplumber.open(file_path) as pdf:
                text_pages = [page.extract_text() or "" for page in pdf.pages]
            return "\n".join(text_pages)
        except Exception as e:
            raise RuntimeError(f"Failed to read PDF file {file_path}: {e}")
            
    def _extract_email(self, text: str) -> Optional[str]:
        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        return match.group(0).strip() if match else None
        
    def _extract_phone(self, text: str) -> Optional[str]:
        # Match standard phone shapes (e.g. +1-555-555-5555, (555) 555-5555, etc.)
        match = re.search(r'\+?\d[\d\-\(\)\s]{7,}\d', text)
        return match.group(0).strip() if match else None
        
    def _extract_name(self, text: str) -> Optional[str]:
        # Look at the first 5 non-empty lines of text
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines[:5]:
            # Skip contact/location/label details
            if "@" in line or any(char.isdigit() for char in line) and len(line) < 15:
                continue
            if line.lower() in ["curriculum vitae", "resume", "cv", "summary", "contact"]:
                continue
            # Assume candidate name has 2 to 4 words
            words = line.split()
            if 2 <= len(words) <= 4:
                return line
        return None
        
    def _extract_country(self, text: str) -> Optional[str]:
        # Match common country names/codes in the header section
        common_countries = [
            "United States", "USA", "US", "India", "IN", "United Kingdom", "UK", 
            "GB", "Canada", "CA", "Germany", "DE", "France", "FR"
        ]
        # Look only at the top 10 lines of the document
        lines = [line.lower() for line in text.split("\n")[:10]]
        for line in lines:
            for country in common_countries:
                if re.search(r'\b' + re.escape(country.lower()) + r'\b', line):
                    return country
        return None
        
    def _split_sections(self, text: str) -> Dict[str, str]:
        lines = text.split("\n")
        sections = {}
        current_section = "header"
        section_text = []
        
        headers = {
            "education": ["education", "academic background", "studies", "academic history"],
            "experience": ["experience", "work experience", "employment history", "professional experience", "work history"],
            "skills": ["skills", "technical skills", "skills & expertise", "core competencies"],
        }
        
        for line in lines:
            cleaned_line = line.strip()
            if not cleaned_line:
                continue
                
            is_header = False
            for sec_key, keywords in headers.items():
                for kw in keywords:
                    if re.match(r'^' + re.escape(kw) + r'\b', cleaned_line.lower()):
                        if len(cleaned_line.split()) <= 4:
                            if current_section:
                                sections[current_section] = "\n".join(section_text)
                            current_section = sec_key
                            section_text = []
                            is_header = True
                            break
                if is_header:
                    break
            if not is_header:
                section_text.append(line)
                
        if current_section:
            sections[current_section] = "\n".join(section_text)
            
        return sections
        
    def _extract_skills(self, skills_text: str) -> List[str]:
        # Check text segments split by common delimiters
        candidates = re.split(r'[,;|\n•·]|\s{2,}', skills_text)
        extracted = []
        for cand in candidates:
            cand_clean = cand.strip()
            if not cand_clean:
                continue
            for skill in KNOWN_SKILLS:
                if re.search(r'\b' + re.escape(skill) + r'\b', cand_clean, re.IGNORECASE):
                    if skill not in extracted:
                        extracted.append(skill)
                        
        # Global fallback if section splitting missed some skills
        if not extracted:
            for skill in KNOWN_SKILLS:
                if re.search(r'\b' + re.escape(skill) + r'\b', skills_text, re.IGNORECASE):
                    if skill.lower() == "go" and not re.search(r'\bGo\b', skills_text):
                        continue
                    if skill not in extracted:
                        extracted.append(skill)
        return extracted
        
    def _parse_education(self, edu_text: str) -> List[EducationRaw]:
        if not edu_text:
            return []
            
        lines = [line.strip() for line in edu_text.split("\n") if line.strip()]
        education = []
        current_edu = {}
        
        degrees = ["B.S.", "M.S.", "Ph.D.", "B.A.", "M.A.", "Bachelor", "Master", "Doctor", "PhD", "B.Tech", "M.Tech", "MBA"]
        
        for line in lines:
            school_match = re.search(r'(University|College|Institute|School|Academy|Tech)\b', line, re.IGNORECASE)
            
            degree_match = None
            for deg in degrees:
                if re.search(r'\b' + re.escape(deg) + r'\b', line, re.IGNORECASE):
                    degree_match = deg
                    break
                    
            date_match = re.findall(r'\b(19\d{2}|20\d{2})\b', line)
            
            if school_match and current_edu:
                education.append(EducationRaw(**current_edu))
                current_edu = {}
                
            if school_match:
                current_edu["institution"] = line
            elif degree_match:
                current_edu["degree"] = degree_match
                field = line.replace(degree_match, "").strip(" ,-:")
                if field:
                    current_edu["field_of_study"] = field
                    
            if date_match:
                if len(date_match) >= 2:
                    current_edu["start_date"] = date_match[0]
                    current_edu["end_date"] = date_match[1]
                elif len(date_match) == 1:
                    current_edu["end_date"] = date_match[0]
                    
        if current_edu:
            education.append(EducationRaw(**current_edu))
            
        return education
        
    def _parse_experience(self, exp_text: str) -> List[ExperienceRaw]:
        if not exp_text:
            return []
            
        lines = [line.strip() for line in exp_text.split("\n") if line.strip()]
        experience = []
        current_exp = {}
        
        role_keywords = ["Engineer", "Developer", "Manager", "Lead", "Analyst", "Consultant", "Intern", "Specialist", "Architect", "Designer"]
        
        for line in lines:
            # Common date shapes
            date_pattern = r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,-]*\d{4}\b|\b\d{4}[-/]\d{2}\b|\b\d{4}\b|Present|Current'
            dates = re.findall(date_pattern, line, re.IGNORECASE)
            
            company_match = re.search(r'\b(Inc\.|Corp\.|Co\.|Ltd\.|LLC|Group|Solutions|Technologies|Systems)\b', line, re.IGNORECASE)
            
            role_match = None
            for rkw in role_keywords:
                if re.search(r'\b' + re.escape(rkw) + r'\b', line, re.IGNORECASE):
                    role_match = line
                    break
                    
            date_range_match = re.search(rf'({date_pattern})\s*[-–to]+\s*({date_pattern})', line, re.IGNORECASE)
            
            if (company_match or role_match) and current_exp and ("company" in current_exp or "role" in current_exp):
                experience.append(ExperienceRaw(**current_exp))
                current_exp = {}
                
            # If comma-delimited, attempt smart split (e.g. "Google, Software Engineer")
            if "," in line and not company_match:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    for rkw in role_keywords:
                        if re.search(r'\b' + re.escape(rkw) + r'\b', parts[1], re.IGNORECASE):
                            current_exp["company"] = parts[0]
                            current_exp["role"] = parts[1]
                            break
                            
            if company_match:
                current_exp["company"] = line
            elif role_match and not current_exp.get("role"):
                current_exp["role"] = line
                
            if date_range_match:
                current_exp["start_date"] = date_range_match.group(1).strip()
                current_exp["end_date"] = date_range_match.group(2).strip()
            elif dates and not current_exp.get("end_date"):
                if len(dates) >= 2:
                    current_exp["start_date"] = dates[0]
                    current_exp["end_date"] = dates[1]
                else:
                    current_exp["end_date"] = dates[0]
                    
        if current_exp:
            experience.append(ExperienceRaw(**current_exp))
            
        return experience
