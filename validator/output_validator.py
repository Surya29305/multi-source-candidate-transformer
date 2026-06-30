import re
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, field_validator, ValidationError

logger = logging.getLogger("CandidateTransformer")

# Pydantic validation models for individual fields
class EmailFieldModel(BaseModel):
    value: str

    @field_validator("value")
    @classmethod
    def validate_email(cls, v: str) -> str:
        # Simple email structure regex
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', v):
            raise ValueError("Invalid email format")
        return v

class PhoneFieldModel(BaseModel):
    value: str

    @field_validator("value")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # E.164 format regex: + followed by 7 to 15 digits
        if not re.match(r'^\+\d{7,15}$', v):
            raise ValueError("Phone number must be in E.164 format (e.g., +15555555555)")
        return v

class CountryFieldModel(BaseModel):
    value: str

    @field_validator("value")
    @classmethod
    def validate_country(cls, v: str) -> str:
        # ISO-3166 Alpha-2 code: exactly 2 uppercase letters
        if not re.match(r'^[A-Z]{2}$', v):
            raise ValueError("Country must be a 2-letter ISO-3166 Alpha-2 uppercase code")
        return v

class OutputValidator:
    def validate(self, projected_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates the projected data structure based on field schemas.
        If a field value is invalid under its Pydantic validator, it is set 
        to None instead of raising an error.
        """
        # Shallow copy of the projected data to avoid side effects
        data_copy = dict(projected_data)
        fields_config = config.get("fields", {})
        
        for canonical_path, field_cfg in fields_config.items():
            rename_to = field_cfg.get("rename", canonical_path)
            
            # Find the value in the output dict
            nested_container, key = self._get_nested_container_and_key(data_copy, rename_to)
            if nested_container is None or key not in nested_container:
                continue
                
            projected_item = nested_container[key]
            if projected_item is None:
                continue
                
            # Extract raw value and check validation rules
            raw_val = self._extract_raw_value(projected_item)
            if raw_val is None:
                continue
                
            is_valid = True
            
            # Validate based on the canonical field type
            try:
                if canonical_path == "email":
                    EmailFieldModel(value=raw_val)
                elif canonical_path == "phone":
                    PhoneFieldModel(value=raw_val)
                elif canonical_path == "country":
                    CountryFieldModel(value=raw_val)
            except ValidationError as e:
                logger.warning(
                    f"Validation failed for field '{canonical_path}' (value: '{raw_val}'). "
                    f"Setting value to null. Reason: {e.errors()[0]['msg']}"
                )
                is_valid = False
                
            if not is_valid:
                self._nullify_field(nested_container, key)
                
        return data_copy
        
    def _get_nested_container_and_key(self, d: dict, path: str) -> tuple:
        """
        Returns the parent dictionary and the target key for a dot-separated path.
        """
        parts = path.split(".")
        current = d
        for part in parts[:-1]:
            if not isinstance(current, dict) or part not in current:
                return None, None
            current = current[part]
        return current, parts[-1]
        
    def _extract_raw_value(self, item: Any) -> Any:
        """
        Gets the raw value from a projected item.
        If the value is wrapped in confidence/provenance dict, returns item['value'].
        """
        if isinstance(item, dict) and "value" in item:
            return item["value"]
        return item
        
    def _nullify_field(self, container: dict, key: str) -> None:
        """
        Nullifies the field. If it is wrapped in confidence/provenance dict,
        sets item['value'] = None. Otherwise sets the entire field to None.
        """
        item = container[key]
        if isinstance(item, dict) and "value" in item:
            item["value"] = None
        else:
            container[key] = None
