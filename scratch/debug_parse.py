import json
import sys
sys.path.append('.')
from parsers import PdfParser, JsonParser, CsvParser, LinkedinParser

def debug():
    print("--- ATS ---")
    ats = JsonParser().parse("sample_data/ats_candidate.json")
    print(ats.model_dump_json(indent=2))
    
    print("\n--- CSV ---")
    csv = CsvParser().parse("sample_data/recruiter_candidate.csv")
    print(csv.model_dump_json(indent=2))
    
    print("\n--- RESUME ---")
    resume = PdfParser().parse("sample_data/resume_candidate.pdf")
    print(resume.model_dump_json(indent=2))
    
    print("\n--- LINKEDIN ---")
    linkedin = LinkedinParser().parse("sample_data/linkedin_candidate.txt")
    print(linkedin.model_dump_json(indent=2))

if __name__ == '__main__':
    debug()
