from validator import OutputValidator

def test_validator_safe_null_fallback():
    validator = OutputValidator()
    
    config = {
        "fields": {
            "emails": {"rename": "email_addresses", "path": "emails"},
            "phones": {"rename": "phones", "path": "phones"},
            "location": {"rename": "location", "path": "location"}
        }
    }
    
    # 1. Plain dictionary format validation (metadata disabled)
    bad_data_plain = {
        "email_addresses": ["invalid-email"],
        "phones": ["+15555555555"],
        "location": {"country": "US"}
    }
    
    validated_plain = validator.validate(bad_data_plain, config)
    assert validated_plain["email_addresses"] == []  # set to empty list
    assert validated_plain["phones"] == ["+15555555555"]
    assert validated_plain["location"]["country"] == "US"

    # 2. Metadata dictionary format validation (metadata enabled)
    bad_data_metadata = {
        "email_addresses": [{"value": "invalid-email", "confidence": 0.8}],
        "phones": [{"value": "invalid-phone", "confidence": 0.9}],
        "location": {"value": {"country": "US"}, "confidence": 1.0}
    }
    
    validated_meta = validator.validate(bad_data_metadata, config)
    assert validated_meta["email_addresses"] == []          # list wiped out
    assert validated_meta["phones"] == []                   # list wiped out
    assert validated_meta["location"]["value"]["country"] == "US"
