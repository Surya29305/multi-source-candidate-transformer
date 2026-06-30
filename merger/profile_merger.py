import re
import hashlib
from datetime import datetime
from typing import List, Optional, Any, Dict
from models import (
    CanonicalCandidate, RawCandidate, FieldValue, Provenance, 
    EducationCanonical, ExperienceCanonical, LocationCanonical, LinksCanonical
)
from normalizers import normalize_phone, normalize_date, normalize_skill, normalize_country, normalize_url

class ProfileMerger:
    def merge(self, *args, **kwargs) -> CanonicalCandidate:
        """
        Merges a variable collection of raw candidates into a single CanonicalCandidate.
        Supports:
          - Dict argument: merge({"ats": ats_raw, "resume": resume_raw})
          - Kwargs: merge(ats=ats_raw, resume=resume_raw)
          - Positional arguments (backward compatible): merge(resume_raw, ats_raw)
        Priority: ATS > CSV > Resume > LinkedIn.
        """
        sources = {}
        if args:
            if isinstance(args[0], dict):
                sources = args[0]
            else:
                if len(args) >= 1:
                    sources["resume"] = args[0]
                if len(args) >= 2:
                    sources["ats"] = args[1]
                if len(args) >= 3:
                    sources["csv"] = args[2]
                if len(args) >= 4:
                    sources["linkedin"] = args[3]
        for k, v in kwargs.items():
            sources[k] = v
            
        priority_map = {"linkedin": 0, "resume": 1, "csv": 2, "ats": 3}
        
        canonical_profiles = []
        for src_name, raw in sources.items():
            if raw:
                canonical = self._to_canonical(raw, src_name)
                priority = priority_map.get(src_name.lower(), -1)
                canonical_profiles.append((priority, canonical))
                
        # Sort by priority ascending (lowest to highest) so higher priority is merged on top
        canonical_profiles.sort(key=lambda x: x[0])
        
        final_prof = CanonicalCandidate()
        for _, profile in canonical_profiles:
            final_prof = self._merge_profiles(profile, final_prof)
            
        final_prof.years_experience = self._compute_years_experience(final_prof.experience)
        
        if not final_prof.candidate_id:
            final_prof.candidate_id = self._generate_candidate_id(final_prof)
            
        return final_prof
        
    def _generate_candidate_id(self, prof: CanonicalCandidate) -> Optional[FieldValue]:
        name = prof.full_name.value if prof.full_name else ""
        email = prof.emails[0].value if prof.emails else ""
        phone = prof.phones[0].value if prof.phones else ""
        
        raw_str = f"{name}|{email}|{phone}".lower().encode('utf-8')
        hash_val = hashlib.sha256(raw_str).hexdigest()
        
        return FieldValue(
            value=hash_val,
            confidence=1.0,
            provenance=[Provenance(field="candidate_id", source="system", extraction_method="deterministic_hash")]
        )

    def _compute_years_experience(self, exp_list: List[FieldValue[ExperienceCanonical]]) -> Optional[FieldValue]:
        if not exp_list:
            return None
            
        intervals = []
        for exp in exp_list:
            v = exp.value
            if not v.start_date: continue
            try:
                start = datetime.strptime(v.start_date, "%Y-%m")
                end = datetime.strptime(v.end_date, "%Y-%m") if v.end_date and v.end_date.lower() != "present" else datetime.now()
                if end < start: continue
                intervals.append((start, end))
            except Exception:
                pass
                
        if not intervals:
            return None
            
        intervals.sort(key=lambda x: x[0])
        merged = [intervals[0]]
        for current in intervals[1:]:
            prev = merged[-1]
            if current[0] <= prev[1]:
                merged[-1] = (prev[0], max(prev[1], current[1]))
            else:
                merged.append(current)
                
        total_months = sum((end.year - start.year) * 12 + (end.month - start.month) for start, end in merged)
        if total_months == 0:
            return None
            
        return FieldValue(
            value=round(total_months / 12.0, 1),
            confidence=1.0,
            provenance=[Provenance(field="years_experience", source="system", extraction_method="computed")]
        )

    def _to_canonical(self, raw: RawCandidate, source: str) -> CanonicalCandidate:
        source_cfg = {
            "ats": {"direct": 0.90, "heuristic": 0.90, "method_direct": "ats_json", "method_heuristic": "ats_json"},
            "csv": {"direct": 0.85, "heuristic": 0.85, "method_direct": "csv_structure", "method_heuristic": "csv_structure"},
            "resume": {"direct": 0.80, "heuristic": 0.60, "method_direct": "pdf_structure", "method_heuristic": "regex"},
            "linkedin": {"direct": 0.80, "heuristic": 0.60, "method_direct": "linkedin_structure", "method_heuristic": "regex"}
        }.get(source.lower(), {"direct": 0.70, "heuristic": 0.50, "method_direct": "unknown", "method_heuristic": "unknown"})
        
        conf_direct = source_cfg["direct"]
        conf_heuristic = source_cfg["heuristic"]
        method_direct = source_cfg["method_direct"]
        method_heuristic = source_cfg["method_heuristic"]
        
        def wrap(val: Any, field_name: str, is_heuristic: bool = False) -> Optional[FieldValue]:
            if val is None:
                return None
            return FieldValue(
                value=val,
                confidence=conf_heuristic if is_heuristic else conf_direct,
                provenance=[Provenance(field=field_name, source=source, extraction_method=method_heuristic if is_heuristic else method_direct)]
            )
            
        is_unstructured = source.lower() in ["resume", "linkedin"]
        norm_name = raw.full_name.strip() if raw.full_name else None
        
        emails_canon = []
        for e in raw.emails:
            e_str = e.strip().lower()
            if e_str: emails_canon.append(wrap(e_str, "emails", is_heuristic=is_unstructured))
            
        phones_canon = []
        for p in raw.phones:
            p_str = normalize_phone(p)
            if p_str: phones_canon.append(wrap(p_str, "phones", is_heuristic=is_unstructured))
            
        loc_canon = None
        if raw.location:
            c = normalize_country(raw.location.country)
            loc_val = LocationCanonical(
                city=raw.location.city.strip() if raw.location.city else None,
                region=raw.location.region.strip() if raw.location.region else None,
                country=c
            )
            loc_canon = wrap(loc_val, "location")
            
        links_canon = None
        if raw.links:
            lnk_val = LinksCanonical(
                linkedin=normalize_url(raw.links.linkedin),
                github=normalize_url(raw.links.github),
                portfolio=normalize_url(raw.links.portfolio),
                other=[normalize_url(o) for o in raw.links.other if o.strip()]
            )
            lnk_val.other = [o for o in lnk_val.other if o is not None]
            links_canon = wrap(lnk_val, "links")
            
        headline_canon = wrap(raw.headline.strip(), "headline") if raw.headline else None
        candidate_id = wrap(raw.candidate_id.strip(), "candidate_id") if raw.candidate_id else None

        skills_canonical = []
        seen_skills = set()
        for skill in raw.skills:
            ns = normalize_skill(skill)
            if ns and ns.lower() not in seen_skills:
                seen_skills.add(ns.lower())
                skills_canonical.append(wrap(ns, "skills"))
                
        edu_canonical = []
        for edu in raw.education:
            if not edu.institution: continue
            edu_val = EducationCanonical(
                institution=edu.institution.strip(),
                degree=edu.degree.strip() if edu.degree else None,
                field_of_study=edu.field_of_study.strip() if edu.field_of_study else None,
                start_date=normalize_date(edu.start_date),
                end_date=normalize_date(edu.end_date)
            )
            edu_canonical.append(wrap(edu_val, "education"))
            
        exp_canonical = []
        for exp in raw.experience:
            if not exp.company: continue
            exp_val = ExperienceCanonical(
                company=exp.company.strip(),
                role=exp.role.strip() if exp.role else None,
                start_date=normalize_date(exp.start_date),
                end_date=normalize_date(exp.end_date),
                location=exp.location.strip() if exp.location else None
            )
            exp_canonical.append(wrap(exp_val, "experience"))
            
        return CanonicalCandidate(
            candidate_id=candidate_id,
            full_name=wrap(norm_name, "full_name"),
            emails=emails_canon,
            phones=phones_canon,
            location=loc_canon,
            links=links_canon,
            headline=headline_canon,
            skills=skills_canonical,
            education=edu_canonical,
            experience=exp_canonical
        )
        
    def _merge_profiles(self, p1: CanonicalCandidate, p2: CanonicalCandidate) -> CanonicalCandidate:
        """p1 is higher priority (e.g. ATS)."""
        return CanonicalCandidate(
            candidate_id=self._merge_single_field("candidate_id", p1.candidate_id, p2.candidate_id, p1_priority=True),
            full_name=self._merge_single_field("full_name", p1.full_name, p2.full_name, p1_priority=True),
            emails=self._merge_list_field(p1.emails, p2.emails, lambda x: x.lower()),
            phones=self._merge_list_field(p1.phones, p2.phones, lambda x: x),
            location=self._merge_location(p1.location, p2.location, p1_priority=True),
            links=self._merge_links(p1.links, p2.links, p1_priority=True),
            headline=self._merge_single_field("headline", p1.headline, p2.headline, p1_priority=True),
            skills=self._merge_skills(p1.skills, p2.skills),
            education=self._merge_education(p1.education, p2.education),
            experience=self._merge_experience(p1.experience, p2.experience)
        )

    def _merge_single_field(self, field_name: str, f1: Optional[FieldValue], f2: Optional[FieldValue], p1_priority: bool = True) -> Optional[FieldValue]:
        if not f1 and not f2: return None
        if f1 and not f2: return f1
        if f2 and not f1: return f2
        
        if f1.value == f2.value:
            return FieldValue(
                value=f1.value,
                confidence=1.0,
                provenance=f1.provenance + f2.provenance
            )
            
        if p1_priority:
            selected_val = f1.value
            conf = max(f1.confidence, f2.confidence) - 0.1 # conflict reduction
            prov = f1.provenance + f2.provenance
        else:
            selected_val = f1.value if f1.confidence >= f2.confidence else f2.value
            conf = max(f1.confidence, f2.confidence) - 0.1
            prov = f1.provenance + f2.provenance
            
        return FieldValue(value=selected_val, confidence=round(conf, 2), provenance=prov)
        
    def _merge_location(self, f1: Optional[FieldValue[LocationCanonical]], f2: Optional[FieldValue[LocationCanonical]], p1_priority: bool = True) -> Optional[FieldValue[LocationCanonical]]:
        if not f1 and not f2: return None
        if f1 and not f2: return f1
        if f2 and not f1: return f2
        
        v1, v2 = f1.value, f2.value
        merged_val = LocationCanonical(
            city=v1.city or v2.city,
            region=v1.region or v2.region,
            country=v1.country or v2.country
        )
        
        if v1.city == v2.city and v1.country == v2.country:
            conf = 1.0
        else:
            conf = max(f1.confidence, f2.confidence) - 0.1
            
        return FieldValue(value=merged_val, confidence=round(conf, 2), provenance=f1.provenance + f2.provenance)

    def _merge_links(self, f1: Optional[FieldValue[LinksCanonical]], f2: Optional[FieldValue[LinksCanonical]], p1_priority: bool = True) -> Optional[FieldValue[LinksCanonical]]:
        if not f1 and not f2: return None
        if f1 and not f2: return f1
        if f2 and not f1: return f2
        
        v1, v2 = f1.value, f2.value
        merged_val = LinksCanonical(
            linkedin=v1.linkedin or v2.linkedin,
            github=v1.github or v2.github,
            portfolio=v1.portfolio or v2.portfolio,
            other=list(set(v1.other + v2.other))
        )
        
        return FieldValue(value=merged_val, confidence=max(f1.confidence, f2.confidence), provenance=f1.provenance + f2.provenance)

    def _merge_list_field(self, l1: List[FieldValue], l2: List[FieldValue], key_func) -> List[FieldValue]:
        merged = []
        l2_by_key = {key_func(i.value): i for i in l2}
        processed_keys = set()
        
        for item in l1:
            k = key_func(item.value)
            if k in l2_by_key:
                match = l2_by_key[k]
                merged.append(FieldValue(
                    value=item.value,
                    confidence=1.0,
                    provenance=item.provenance + match.provenance
                ))
                processed_keys.add(k)
            else:
                merged.append(item)
                
        for k, item in l2_by_key.items():
            if k not in processed_keys:
                merged.append(item)
        return merged

    def _merge_skills(self, s1: List[FieldValue[str]], s2: List[FieldValue[str]]) -> List[FieldValue[str]]:
        return self._merge_list_field(s1, s2, lambda x: x.lower())
        
    def _merge_education(self, edu1: List[FieldValue[EducationCanonical]], edu2: List[FieldValue[EducationCanonical]]) -> List[FieldValue[EducationCanonical]]:
        merged_edu = []
        edu2_matched_indices = set()
        
        for item1 in edu1:
            match_index = -1
            for idx, item2 in enumerate(edu2):
                if idx not in edu2_matched_indices and self._education_items_match(item1.value, item2.value):
                    match_index = idx
                    break
                    
            if match_index != -1:
                item2 = edu2[match_index]
                edu2_matched_indices.add(match_index)
                
                val1, val2 = item1.value, item2.value
                merged_val = EducationCanonical(
                    institution=val1.institution or val2.institution,
                    degree=val1.degree or val2.degree,
                    field_of_study=val1.field_of_study or val2.field_of_study,
                    start_date=val1.start_date or val2.start_date,
                    end_date=val1.end_date or val2.end_date
                )
                
                merged_edu.append(FieldValue(
                    value=merged_val,
                    confidence=1.0,
                    provenance=item1.provenance + item2.provenance
                ))
            else:
                merged_edu.append(item1)
                
        for idx, item2 in enumerate(edu2):
            if idx not in edu2_matched_indices:
                merged_edu.append(item2)
        return merged_edu
        
    def _merge_experience(self, exp1: List[FieldValue[ExperienceCanonical]], exp2: List[FieldValue[ExperienceCanonical]]) -> List[FieldValue[ExperienceCanonical]]:
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
                
                val1, val2 = item1.value, item2.value
                merged_val = ExperienceCanonical(
                    company=val1.company or val2.company,
                    role=val1.role or val2.role,
                    start_date=val1.start_date or val2.start_date,
                    end_date=val1.end_date or val2.end_date,
                    location=val1.location or val2.location
                )
                
                merged_exp.append(FieldValue(
                    value=merged_val,
                    confidence=1.0,
                    provenance=item1.provenance + item2.provenance
                ))
            else:
                merged_exp.append(item1)
                
        for idx, item2 in enumerate(exp2):
            if idx not in exp2_matched_indices:
                merged_exp.append(item2)
        return merged_exp
        
    def _education_items_match(self, edu1: EducationCanonical, edu2: EducationCanonical) -> bool:
        if not edu1.institution or not edu2.institution: return False
        inst1 = edu1.institution.lower().replace("university", "").replace("college", "").strip()
        inst2 = edu2.institution.lower().replace("university", "").replace("college", "").strip()
        if inst1 == inst2 or inst1 in inst2 or inst2 in inst1:
            deg1 = (edu1.degree or "").lower()
            deg2 = (edu2.degree or "").lower()
            if not deg1 or not deg2: return True
            if deg1[0] == deg2[0]: return True
            if ("ph" in deg1 or "doctor" in deg1) and ("ph" in deg2 or "doctor" in deg2): return True
        return False
        
    def _experience_items_match(self, exp1: ExperienceCanonical, exp2: ExperienceCanonical) -> bool:
        if not exp1.company or not exp2.company: return False
        suffixes = [r'\binc\b', r'\bcorp\b', r'\bco\b', r'\bltd\b', r'\bllc\b', r'\bsystems\b', r'\btechnologies\b']
        c1, c2 = exp1.company.lower(), exp2.company.lower()
        for s in suffixes:
            c1 = re.sub(s, "", c1)
            c2 = re.sub(s, "", c2)
        c1, c2 = c1.strip(), c2.strip()
        return c1 == c2 or c1 in c2 or c2 in c1
