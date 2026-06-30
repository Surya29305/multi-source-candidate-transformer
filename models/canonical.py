from typing import List, Optional
from pydantic import BaseModel, Field
from models.provenance import FieldValue

class EducationCanonical(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class ExperienceCanonical(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location: Optional[str] = None

class CanonicalCandidate(BaseModel):
    name: Optional[FieldValue[str]] = None
    email: Optional[FieldValue[str]] = None
    phone: Optional[FieldValue[str]] = None
    skills: List[FieldValue[str]] = Field(default_factory=list)
    education: List[FieldValue[EducationCanonical]] = Field(default_factory=list)
    experience: List[FieldValue[ExperienceCanonical]] = Field(default_factory=list)
    country: Optional[FieldValue[str]] = None

    def calculate_overall_confidence(self) -> float:
        """
        Calculate overall confidence score as the average of the confidences of all present fields.
        For list fields (skills, education, experience), we compute the average of their 
        elements' confidences if any items are present.
        """
        confidences = []
        
        for field_name in ["name", "email", "phone", "country"]:
            field_val = getattr(self, field_name)
            if field_val is not None:
                confidences.append(field_val.confidence)
                
        if self.skills:
            skills_conf = sum(s.confidence for s in self.skills) / len(self.skills)
            confidences.append(skills_conf)
            
        if self.education:
            edu_conf = sum(e.confidence for e in self.education) / len(self.education)
            confidences.append(edu_conf)
            
        if self.experience:
            exp_conf = sum(e.confidence for e in self.experience) / len(self.experience)
            confidences.append(exp_conf)
            
        if not confidences:
            return 0.0
            
        return round(sum(confidences) / len(confidences), 2)
