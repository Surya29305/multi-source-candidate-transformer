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

class LocationCanonical(BaseModel):
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None

class LinksCanonical(BaseModel):
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    other: List[str] = Field(default_factory=list)

class CanonicalCandidate(BaseModel):
    candidate_id: Optional[FieldValue[str]] = None
    full_name: Optional[FieldValue[str]] = None
    emails: List[FieldValue[str]] = Field(default_factory=list)
    phones: List[FieldValue[str]] = Field(default_factory=list)
    location: Optional[FieldValue[LocationCanonical]] = None
    links: Optional[FieldValue[LinksCanonical]] = None
    headline: Optional[FieldValue[str]] = None
    years_experience: Optional[FieldValue[float]] = None
    skills: List[FieldValue[str]] = Field(default_factory=list)
    experience: List[FieldValue[ExperienceCanonical]] = Field(default_factory=list)
    education: List[FieldValue[EducationCanonical]] = Field(default_factory=list)

    def calculate_overall_confidence(self) -> float:
        """
        Calculate overall confidence score as the average of the confidences of all present fields.
        """
        confidences = []
        
        for field_name in ["candidate_id", "full_name", "location", "links", "headline", "years_experience"]:
            field_val = getattr(self, field_name)
            if field_val is not None:
                confidences.append(field_val.confidence)
                
        for list_field in [self.emails, self.phones, self.skills, self.experience, self.education]:
            if list_field:
                avg_conf = sum(i.confidence for i in list_field) / len(list_field)
                confidences.append(avg_conf)
            
        if not confidences:
            return 0.0
            
        return round(sum(confidences) / len(confidences), 2)
