from normalizers import normalize_phone, normalize_date, normalize_skill, normalize_country

def test_phone_normalization():
    # E.164 phone normalization tests
    assert normalize_phone("+1 555-555-5555") == "+15555555555"
    assert normalize_phone("555-555-5555") == "+15555555555"  # defaults to US
    assert normalize_phone("+91 99999 99999") == "+919999999999"
    # Unparseable numbers fall back to clean alphanumerics
    assert normalize_phone("invalid-phone") == "invalid-phone"

def test_date_normalization():
    # YYYY-MM date normalization tests
    assert normalize_date("June 2021") == "2021-06"
    assert normalize_date("2021/06") == "2021-06"
    assert normalize_date("2021-06") == "2021-06"
    assert normalize_date("2021") == "2021-01"
    assert normalize_date("Present") == "Present"
    assert normalize_date("Current") == "Present"

def test_skill_normalization():
    # Skill canonicalization tests
    assert normalize_skill("ML") == "Machine Learning"
    assert normalize_skill("JS") == "JavaScript"
    assert normalize_skill("ReactJS") == "React"
    assert normalize_skill("python") == "Python"
    assert normalize_skill("Docker") == "Docker"
    assert normalize_skill("UnrecognizedSkill") == "UnrecognizedSkill"

def test_country_normalization():
    # ISO-3166 Alpha-2 country code tests
    assert normalize_country("United States") == "US"
    assert normalize_country("USA") == "US"
    assert normalize_country("India") == "IN"
    assert normalize_country("uk") == "GB"
    # Returns capitalized input for unrecognized codes
    assert normalize_country("unknown") == "UNKNOWN"
