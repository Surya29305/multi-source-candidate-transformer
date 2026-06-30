from models import RawCandidate, EducationRaw, ExperienceRaw
from merger import ProfileMerger

def test_merge_conflicts_highest_confidence_wins():
    # ATS maps with 0.9 confidence, Resume maps with 0.8
    # When name fields conflict, the merger selects the ATS value ("John A. Doe") over Resume ("John Doe")
    merger = ProfileMerger()
    resume = RawCandidate(name="John Doe", email="john@example.com")
    ats = RawCandidate(name="John A. Doe", email="john@example.com")
    
    canonical = merger.merge(resume, ats)
    
    assert canonical.name.value == "John A. Doe"
    # Value present in both boosts confidence to 1.0
    assert canonical.name.confidence == 1.0
    # Provenance contains entries for both resume and ats
    provenance_sources = [p.source for p in canonical.name.provenance]
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
