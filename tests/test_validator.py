from validator import OutputValidator

def test_validator_safe_null_fallback():
    validator = OutputValidator()
    
    config = {
        "fields": {
            "email": {"rename": "email_address", "path": "email"},
            "phone": {"rename": "phone", "path": "phone"},
            "country": {"rename": "country", "path": "country"}
        }
    }
    
    # 1. Plain dictionary format validation (metadata disabled)
    bad_data_plain = {
        "email_address": "invalid-email", # invalid
        "phone": "+15555555555",          # valid
        "country": "US"                   # valid
    }
    
    validated_plain = validator.validate(bad_data_plain, config)
    assert validated_plain["email_address"] is None  # set to null
    assert validated_plain["phone"] == "+15555555555"
    assert validated_plain["country"] == "US"

    # 2. Metadata dictionary format validation (metadata enabled)
    bad_data_metadata = {
        "email_address": {"value": "invalid-email", "confidence": 0.8},
        "phone": {"value": "invalid-phone", "confidence": 0.9},
        "country": {"value": "US", "confidence": 1.0}
    }
    
    validated_meta = validator.validate(bad_data_metadata, config)
    assert validated_meta["email_address"]["value"] is None # set to null
    assert validated_meta["phone"]["value"] is None         # set to null
    assert validated_meta["country"]["value"] == "US"
