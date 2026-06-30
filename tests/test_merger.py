from models import RawCandidate, EducationRaw, ExperienceRaw
from merger import ProfileMerger

def test_merge_conflicts_highest_confidence_wins():
    # ATS maps with 0.9 confidence, Resume maps with 0.8
    # When name fields conflict, the merger selects the ATS value ("John A. Doe") over Resume ("John Doe")
    merger = ProfileMerger()
    resume = RawCandidate(full_name="John Doe", emails=["john@example.com"])
    ats = RawCandidate(full_name="John A. Doe", emails=["john@example.com"])
    
    canonical = merger.merge(resume, ats)
    
    assert canonical.full_name.value == "John A. Doe"
    # Conflict reduction applies: max(0.9, 0.8) - 0.1 = 0.8
    assert canonical.full_name.confidence == 0.8
    # Provenance contains entries for both resume and ats
    provenance_sources = [p.source for p in canonical.full_name.provenance]
    assert "resume" in provenance_sources
    assert "ats" in provenance_sources

def test_duplicate_skills_merging():
    # Verify skill lists deduplication and merging
    merger = ProfileMerger()
    resume = RawCandidate(skills=["ReactJS", "Python"])
    ats = RawCandidate(skills=["React", "SQL"])
    
    canonical = merger.merge(resume, ats)
    
    skill_values = [s.value for s in canonical.skills]
    assert len(skill_values) == 3
    assert "React" in skill_values
    assert "Python" in skill_values
    assert "SQL" in skill_values
    
    # React skill (present in both) gets confidence 1.0 and both sources in provenance
    react_field = [s for s in canonical.skills if s.value == "React"][0]
    assert react_field.confidence == 1.0
    assert len(react_field.provenance) == 2
    sources = [p.source for p in react_field.provenance]
    assert "resume" in sources
    assert "ats" in sources

def test_multi_source_priority():
    # Priority: ATS (0.90) > CSV (0.85) > Resume (0.80) > LinkedIn (0.80)
    merger = ProfileMerger()
    
    linkedin = RawCandidate(full_name="Linkedin Name")
    resume = RawCandidate(full_name="Resume Name")
    csv = RawCandidate(full_name="CSV Name")
    ats = RawCandidate(full_name="ATS Name")
    
    # All 4 provided: ATS should win
    c1 = merger.merge(linkedin=linkedin, resume=resume, csv=csv, ats=ats)
    assert c1.full_name.value == "ATS Name"
    
    # ATS missing: CSV should win
    c2 = merger.merge(linkedin=linkedin, resume=resume, csv=csv)
    assert c2.full_name.value == "CSV Name"
    
    # ATS and CSV missing: Resume should win
    c3 = merger.merge(linkedin=linkedin, resume=resume)
    assert c3.full_name.value == "Resume Name"
    
    # Only LinkedIn provided: LinkedIn should win
    c4 = merger.merge(linkedin=linkedin)
    assert c4.full_name.value == "Linkedin Name"

def test_provenance_accumulation_multi_source():
    merger = ProfileMerger()
    linkedin = RawCandidate(emails=["jane@example.com"])
    resume = RawCandidate(emails=["jane@example.com"])
    csv = RawCandidate(emails=["jane@example.com"])
    ats = RawCandidate(emails=["jane@example.com"])
    
    c = merger.merge(linkedin=linkedin, resume=resume, csv=csv, ats=ats)
    
    # Check that we have exactly one email, with 4 provenance items
    assert len(c.emails) == 1
    email_field = c.emails[0]
    assert email_field.confidence == 1.0
    sources = [p.source for p in email_field.provenance]
    assert len(sources) == 4
    assert "linkedin" in sources
    assert "resume" in sources
    assert "csv" in sources
    assert "ats" in sources

def test_optional_source_handling():
    merger = ProfileMerger()
    csv = RawCandidate(full_name="Jane Doe", emails=["jane@example.com"])
    
    # Only 1 source (CSV) provided
    c = merger.merge(csv=csv)
    assert c.full_name.value == "Jane Doe"
    assert len(c.emails) == 1
    assert c.emails[0].value == "jane@example.com"

