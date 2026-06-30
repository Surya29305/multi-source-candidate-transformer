import pytest
from models import CanonicalCandidate, FieldValue, Provenance
from projector import SchemaProjector

def test_projection_config_renaming_and_nested_paths():
    projector = SchemaProjector()
    candidate = CanonicalCandidate(
        name=FieldValue(
            value="John Doe", 
            confidence=0.8, 
            provenance=[Provenance(field="name", source="resume", extraction_method="pdf_structure")]
        ),
        email=FieldValue(
            value="john@example.com", 
            confidence=0.6, 
            provenance=[Provenance(field="email", source="resume", extraction_method="regex")]
        )
    )
    
    config = {
        "fields": {
            "name": {"rename": "personal_info.full_name", "path": "name"},
            "email": {"rename": "email_address", "path": "email"}
        },
        "include_confidence": False,
        "include_provenance": False
    }
    
    output = projector.project(candidate, config)
    
    # Nested field checking
    assert "personal_info" in output
    assert output["personal_info"]["full_name"] == "John Doe"
    assert output["email_address"] == "john@example.com"
    # Metadata properties omitted
    assert "overall_confidence" not in output

def test_projection_missing_field_policy():
    projector = SchemaProjector()
    candidate = CanonicalCandidate(
        name=FieldValue(value="John Doe", confidence=0.8, provenance=[])
    )
    
    # 1. Null policy
    config_null = {
        "fields": {
            "name": {"rename": "name", "path": "name"},
            "email": {"rename": "email", "path": "email"}
        },
        "include_confidence": False,
        "include_provenance": False,
        "missing_field_policy": "null"
    }
    output_null = projector.project(candidate, config_null)
    assert output_null["name"] == "John Doe"
    assert output_null["email"] is None
    
    # 2. Omit policy
    config_omit = {
        "fields": {
            "name": {"rename": "name", "path": "name"},
            "email": {"rename": "email", "path": "email"}
        },
        "include_confidence": False,
        "include_provenance": False,
        "missing_field_policy": "omit"
    }
    output_omit = projector.project(candidate, config_omit)
    assert output_omit["name"] == "John Doe"
    assert "email" not in output_omit
    
    # 3. Error policy
    config_error = {
        "fields": {
            "name": {"rename": "name", "path": "name"},
            "email": {"rename": "email", "path": "email"}
        },
        "missing_field_policy": "error"
    }
    with pytest.raises(ValueError):
        projector.project(candidate, config_error)
