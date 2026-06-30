from typing import Optional

# Standardize common variations to canonical terms
CANONICAL_SKILLS = {
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "java script": "JavaScript",
    "reactjs": "React",
    "react js": "React",
    "react": "React",
    "sql": "SQL",
    "python": "Python",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "aws": "AWS",
    "golang": "Go",
    "go": "Go",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "html": "HTML",
    "css": "CSS",
    "git": "Git",
    "linux": "Linux"
}

def normalize_skill(skill_str: Optional[str]) -> Optional[str]:
    """
    Standardize skill names. If the skill is in our dictionary, it is 
    replaced with the canonical name. Otherwise, it is stripped and preserved.
    """
    if not skill_str:
        return None
        
    cleaned = skill_str.strip()
    cleaned_lower = cleaned.lower()
    return CANONICAL_SKILLS.get(cleaned_lower, cleaned)
