import re
from parsers.pdf_parser import PdfParser
from models.raw import RawCandidate, LinksRaw

class LinkedinParser(PdfParser):
    def parse(self, file_path: str) -> RawCandidate:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read LinkedIn file {file_path}: {e}")
            
        emails = self._extract_emails(text)
        phones = self._extract_phones(text)
        name = self._extract_name(text)
        location = self._extract_location(text)
        links = self._extract_links(text)
        headline = self._extract_headline(text, name)
        
        # Specifically extract LinkedIn profile link if not caught by general regex
        if not links:
            links = LinksRaw()
            
        if not links.linkedin:
            li_match = re.search(r'(?:linkedin\.com/in/[\w\.-]+)', text, re.IGNORECASE)
            if li_match:
                links.linkedin = li_match.group(0).strip()
                
        sections = self._split_sections(text)
        
        skills = self._extract_skills(sections.get("skills", text))
        education = self._parse_education(sections.get("education", ""))
        experience = self._parse_experience(sections.get("experience", ""))
        
        return RawCandidate(
            full_name=name,
            emails=emails,
            phones=phones,
            location=location,
            links=links,
            headline=headline,
            skills=skills,
            education=education,
            experience=experience
        )
