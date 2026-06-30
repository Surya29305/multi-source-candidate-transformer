import re
from typing import List, Optional, Any
from models import (
    CanonicalCandidate, RawCandidate, FieldValue, Provenance, 
    EducationCanonical, ExperienceCanonical, EducationRaw, ExperienceRaw
)
from normalizers import normalize_phone, normalize_date, normalize_skill, normalize_country

class ProfileMerger:
    def merge(self, resume_raw: Optional[RawCandidate], ats_raw: Optional[RawCandidate]) -> CanonicalCandidate:
        """
        Merges raw candidate inputs from Resume and ATS into a single CanonicalCandidate.
        Handles single-source scenarios gracefully.
        """
        profile_resume = self._to_canonical(resume_raw, "resume") if resume_raw else None
        profile_ats = self._to_canonical(ats_raw, "ats") if ats_raw else None
        
        if profile_resume and not profile_ats:
            return profile_resume
        if profile_ats and not profile_resume:
            return profile_ats
        if not profile_resume and not profile_ats:
            return CanonicalCandidate()
            
        # Perform merge of both profiles
        return self._merge_profiles(profile_resume, profile_ats)
        
    def _to_canonical(self, raw: RawCandidate, source: str) -> CanonicalCandidate:
        """
        Converts a RawCandidate into a CanonicalCandidate, normalizing values
        and setting initial confidence and provenance details.
        """
        # Determine extraction methods and confidences
        is_resume = source == "resume"
        method_direct = "pdf_structure" if is_resume else "ats_json"
        method_heuristic = "regex" if is_resume else "ats_json"
        
        conf_direct = 0.8 if is_resume else 0.9
        conf_heuristic = 0.6 if is_resume else 0.9
        
        # Helper to wrap field value
        def wrap(val: Any, field_name: str, is_heuristic: bool = False) -> Optional[FieldValue]:
            if val is None:
                return None
            return FieldValue(
                value=val,
                confidence=conf_heuristic if is_heuristic else conf_direct,
                provenance=[Provenance(field=field_name, source=source, extraction_method=method_heuristic if is_heuristic else method_direct)]
            )
            
        # Normalize fields
        norm_name = raw.name.strip() if raw.name else None
        norm_email = raw.email.strip().lower() if raw.email else None
        norm_phone = normalize_phone(raw.phone)
        norm_country = normalize_country(raw.country)
        
        # Skills
        skills_canonical = []
        seen_skills = set()
        for skill in raw.skills:
            ns = normalize_skill(skill)
            if ns and ns.lower() not in seen_skills:
                seen_skills.add(ns.lower())
                skills_canonical.append(wrap(ns, "skills"))
                
        # Education
        edu_canonical = []
        for edu in raw.education:
            if not edu.institution:
                continue
            edu_val = EducationCanonical(
                institution=edu.institution.strip(),
                degree=edu.degree.strip() if edu.degree else None,
                field_of_study=edu.field_of_study.strip() if edu.field_of_study else None,
                start_date=normalize_date(edu.start_date),
                end_date=normalize_date(edu.end_date)
            )
            edu_canonical.append(wrap(edu_val, "education"))
            
        # Experience
        exp_canonical = []
        for exp in raw.experience:
            if not exp.company:
                continue
            exp_val = ExperienceCanonical(
                company=exp.company.strip(),
                role=exp.role.strip() if exp.role else None,
                start_date=normalize_date(exp.start_date),
                end_date=normalize_date(exp.end_date),
                location=exp.location.strip() if exp.location else None
            )
            exp_canonical.append(wrap(exp_val, "experience"))
            
        return CanonicalCandidate(
            name=wrap(norm_name, "name"),
            email=wrap(norm_email, "email", is_heuristic=is_resume), # regex extracted in PDF
            phone=wrap(norm_phone, "phone", is_heuristic=is_resume), # regex extracted in PDF
            skills=skills_canonical,
            education=edu_canonical,
            experience=exp_canonical,
            country=wrap(norm_country, "country")
        )
        
    def _merge_profiles(self, p1: CanonicalCandidate, p2: CanonicalCandidate) -> CanonicalCandidate:
        """
        Merges two canonical candidate profiles together.
        """
        return CanonicalCandidate(
            name=self._merge_single_field("name", p1.name, p2.name),
            email=self._merge_single_field("email", p1.email, p2.email),
            phone=self._merge_single_field("phone", p1.phone, p2.phone),
            skills=self._merge_skills(p1.skills, p2.skills),
            education=self._merge_education(p1.education, p2.education),
            experience=self._merge_experience(p1.experience, p2.experience),
            country=self._merge_single_field("country", p1.country, p2.country)
        )
        
    def _merge_single_field(self, field_name: str, f1: Optional[FieldValue], f2: Optional[FieldValue]) -> Optional[FieldValue]:
        """
        Merge two single-value fields, selecting the one with higher confidence,
        boosting confidence to 1.0 if present in both, and tracking provenance.
        """
        if not f1 and not f2:
            return None
        if f1 and not f2:
            return f1
        if f2 and not f1:
            return f2
            
        # Present in both sources
        # Select value based on higher confidence, fallback to f1 if equal
        selected_val = f1.value if f1.confidence >= f2.confidence else f2.value
        
        # Combine provenances
        merged_provenance = f1.provenance + f2.provenance
        
        return FieldValue(
            value=selected_val,
            confidence=1.0,  # Present in both sources
            provenance=merged_provenance
        )
        
    def _merge_skills(self, s1: List[FieldValue[str]], s2: List[FieldValue[str]]) -> List[FieldValue[str]]:
        """
        Merges skills lists. If a skill exists in both lists (case-insensitive),
        it combines them with a confidence of 1.0 and merges provenance.
        """
        merged_skills = []
        s2_by_val = {s.value.lower(): s for s in s2}
        processed_s2_keys = set()
        
        for skill_val in s1:
            key = skill_val.value.lower()
            if key in s2_by_val:
                # Skill is in both sources
                match = s2_by_val[key]
                merged_skills.append(FieldValue(
                    value=skill_val.value, # Keep first casing
                    confidence=1.0,
                    provenance=skill_val.provenance + match.provenance
                ))
                processed_s2_keys.add(key)
            else:
                # Skill in s1 only
                merged_skills.append(skill_val)
                
        # Add remaining skills from s2
        for key, skill_val in s2_by_val.items():
            if key not in processed_s2_keys:
                merged_skills.append(skill_val)
                
        return merged_skills
        
    def _merge_education(self, edu1: List[FieldValue[EducationCanonical]], edu2: List[FieldValue[EducationCanonical]]) -> List[FieldValue[EducationCanonical]]:
        """
        Merges education entries. Matches entries based on institution and degree similarity.
        """
        merged_edu = []
        edu2_matched_indices = set()
        
        for item1 in edu1:
            match_index = -1
            for idx, item2 in enumerate(edu2):
                if idx not in edu2_matched_indices and self._education_items_match(item1.value, item2.value):
                    match_index = idx
                    break
                    
            if match_index != -1:
                # Merged education item
                item2 = edu2[match_index]
                edu2_matched_indices.add(match_index)
                
                # Combine attributes, preferring the one from the higher confidence source
                val1, val2 = item1.value, item2.value
                higher_val = val1 if item1.confidence >= item2.confidence else val2
                lower_val = val2 if item1.confidence >= item2.confidence else val1
                
                # Merge details (fill in blanks in higher-confidence item from lower-confidence item)
                merged_val = EducationCanonical(
                    institution=higher_val.institution,
                    degree=higher_val.degree or lower_val.degree,
                    field_of_study=higher_val.field_of_study or lower_val.field_of_study,
                    start_date=higher_val.start_date or lower_val.start_date,
                    end_date=higher_val.end_date or lower_val.end_date
                )
                
                merged_edu.append(FieldValue(
                    value=merged_val,
                    confidence=1.0,
                    provenance=item1.provenance + item2.provenance
                ))
            else:
                # Present only in source 1
                merged_edu.append(item1)
                
        # Add unmatched from source 2
        for idx, item2 in enumerate(edu2):
            if idx not in edu2_matched_indices:
                merged_edu.append(item2)
                
        return merged_edu
        
    def _merge_experience(self, exp1: List[FieldValue[ExperienceCanonical]], exp2: List[FieldValue[ExperienceCanonical]]) -> List[FieldValue[ExperienceCanonical]]:
        """
        Merges experience entries. Matches entries based on normalized company name similarity.
        """
        merged_exp = []
        exp2_matched_indices = set()
        
        for item1 in exp1:
            match_index = -1
            for idx, item2 in enumerate(exp2):
                if idx not in exp2_matched_indices and self._experience_items_match(item1.value, item2.value):
                    match_index = idx
                    break
                    
            if match_index != -1:
                item2 = exp2[match_index]
                exp2_matched_indices.add(match_index)
                
                # Combine attributes
                val1, val2 = item1.value, item2.value
                higher_val = val1 if item1.confidence >= item2.confidence else val2
                lower_val = val2 if item1.confidence >= item2.confidence else val1
                
                merged_val = ExperienceCanonical(
                    company=higher_val.company,
                    role=higher_val.role or lower_val.role,
                    start_date=higher_val.start_date or lower_val.start_date,
                    end_date=higher_val.end_date or lower_val.end_date,
                    location=higher_val.location or lower_val.location
                )
                
                merged_exp.append(FieldValue(
                    value=merged_val,
                    confidence=1.0,
                    provenance=item1.provenance + item2.provenance
                ))
            else:
                merged_exp.append(item1)
                
        # Add unmatched from source 2
        for idx, item2 in enumerate(exp2):
            if idx not in exp2_matched_indices:
                merged_exp.append(item2)
                
        return merged_exp
        
    def _education_items_match(self, edu1: EducationCanonical, edu2: EducationCanonical) -> bool:
        if not edu1.institution or not edu2.institution:
            return False
            
        # Strip common university tags
        inst1 = edu1.institution.lower().replace("university", "").replace("college", "").strip()
        inst2 = edu2.institution.lower().replace("university", "").replace("college", "").strip()
        
        # Match if institutions overlap significantly
        if inst1 == inst2 or inst1 in inst2 or inst2 in inst1:
            deg1 = (edu1.degree or "").lower()
            deg2 = (edu2.degree or "").lower()
            if not deg1 or not deg2:
                return True
            # Match degrees if they share the same starting letter (e.g. B for B.S./Bachelor)
            if deg1[0] == deg2[0]:
                return True
            if ("ph" in deg1 or "doctor" in deg1) and ("ph" in deg2 or "doctor" in deg2):
                return True
        return False
        
    def _experience_items_match(self, exp1: ExperienceCanonical, exp2: ExperienceCanonical) -> bool:
        if not exp1.company or not exp2.company:
            return False
            
        suffixes = [r'\binc\b', r'\bcorp\b', r'\bco\b', r'\bltd\b', r'\bllc\b', r'\bsystems\b', r'\btechnologies\b']
        c1 = exp1.company.lower()
        c2 = exp2.company.lower()
        
        for s in suffixes:
            c1 = re.sub(s, "", c1)
            c2 = re.sub(s, "", c2)
            
        c1 = c1.strip()
        c2 = c2.strip()
        
        # Match if company names match or overlap
        return c1 == c2 or c1 in c2 or c2 in c1
