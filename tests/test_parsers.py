import pytest
from parsers import CsvParser, LinkedinParser
from models.raw import RawCandidate

def test_csv_parser(tmp_path):
    csv_file = tmp_path / "recruiter.csv"
    csv_file.write_text(
        "Name,Email,Phone,Skills,Current Company,Current Role,Location\n"
        "Alice Smith,alice@example.com,+1 555-123-4567,Python,Google,Software Engineer,\"Seattle, WA\"\n",
        encoding="utf-8"
    )
    
    parser = CsvParser()
    raw = parser.parse(str(csv_file))
    
    assert raw.full_name == "Alice Smith"
    assert raw.emails == ["alice@example.com"]
    assert raw.phones == ["+1 555-123-4567"]
    assert raw.skills == ["Python"]
    assert raw.location.city == "Seattle"
    assert raw.location.region == "WA"
    assert len(raw.experience) == 1
    assert raw.experience[0].company == "Google"
    assert raw.experience[0].role == "Software Engineer"

def test_linkedin_parser(tmp_path):
    linkedin_file = tmp_path / "linkedin.txt"
    linkedin_file.write_text(
        "Bob Jones\n"
        "Data Scientist at Meta\n"
        "Seattle, Washington, United States\n\n"
        "Contact Info:\n"
        "linkedin.com/in/bobjones\n"
        "bob@example.com\n\n"
        "Summary:\n"
        "Specialized in Python and SQL.\n\n"
        "Experience:\n"
        "Meta\n"
        "Data Scientist\n"
        "August 2021 - Present\n"
        "Seattle, WA\n\n"
        "Education:\n"
        "Stanford University\n"
        "M.S. Computer Science\n"
        "2019 - 2021\n\n"
        "Skills:\n"
        "Python, SQL\n",
        encoding="utf-8"
    )
    
    parser = LinkedinParser()
    raw = parser.parse(str(linkedin_file))
    
    assert raw.full_name == "Bob Jones"
    assert raw.emails == ["bob@example.com"]
    assert raw.links.linkedin == "linkedin.com/in/bobjones"
    assert "Python" in raw.skills
    assert "SQL" in raw.skills
