import re
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, field_validator, ValidationError

logger = logging.getLogger("CandidateTransformer")

class EmailFieldModel(BaseModel):
    value: str

    @field_validator("value")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', v):
            raise ValueError("Invalid email format")
        return v

class PhoneFieldModel(BaseModel):
    value: str

    @field_validator("value")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r'^\+\d{7,15}$', v):
            raise ValueError("Phone number must be in E.164 format (e.g., +15555555555)")
        return v

class CountryFieldModel(BaseModel):
    value: str

    @field_validator("value")
    @classmethod
    def validate_country(cls, v: str) -> str:
        if not re.match(r'^[A-Z]{2}$', v):
            raise ValueError("Country must be a 2-letter ISO-3166 Alpha-2 uppercase code")
        return v

class OutputValidator:
    def validate(self, projected_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        data_copy = dict(projected_data)
        fields_config = config.get("fields", {})
        validation_report = {}
        
        for canonical_path, field_cfg in fields_config.items():
            rename_to = field_cfg.get("rename", canonical_path)
            
            nested_container, key = self._get_nested_container_and_key(data_copy, rename_to)
            if nested_container is None or key not in nested_container:
                continue
                
            projected_item = nested_container[key]
            if projected_item is None:
                continue
                
            raw_vals = self._extract_raw_values(projected_item)
            if not raw_vals:
                continue
                
            is_valid = True
            msg = "Required field present"
            
            try:
                if canonical_path == "emails":
                    for rv in raw_vals:
                        EmailFieldModel(value=rv)
                    msg = "Valid email format"
                elif canonical_path == "phones":
                    for rv in raw_vals:
                        PhoneFieldModel(value=rv)
                    msg = "Valid E.164 phone number"
                elif canonical_path == "location":
                    for rv in raw_vals:
                        if rv and "country" in rv and rv["country"]:
                            CountryFieldModel(value=rv["country"])
                    msg = "Location normalized successfully"
            except ValidationError as e:
                logger.warning(
                    f"Validation failed for field '{canonical_path}'. "
                    f"Setting value to null. Reason: {e.errors()[0]['msg']}"
                )
                is_valid = False
                validation_report[canonical_path] = {
                    "status": "failed",
                    "reason": e.errors()[0]['msg']
                }
                
            if is_valid:
                validation_report[canonical_path] = {
                    "status": "passed",
                    "message": msg
                }
                
            if not is_valid:
                self._nullify_field(nested_container, key)
                
        # Only inject the validation report if metadata is enabled
        if config.get("include_metadata", True):
            if "metadata" not in data_copy:
                data_copy["metadata"] = {}
            data_copy["metadata"]["validation_report"] = validation_report
            
        return data_copy
        
    def _get_nested_container_and_key(self, d: dict, path: str) -> tuple:
        parts = path.split(".")
        current = d
        for part in parts[:-1]:
            if not isinstance(current, dict) or part not in current:
                return None, None
            current = current[part]
        return current, parts[-1]
        
    def _extract_raw_values(self, item: Any) -> List[Any]:
        if isinstance(item, list):
            return [self._extract_raw_value(i) for i in item]
        return [self._extract_raw_value(item)]
        
    def _extract_raw_value(self, item: Any) -> Any:
        if isinstance(item, dict) and "value" in item:
            return item["value"]
        return item
        
    def _nullify_field(self, container: dict, key: str) -> None:
        item = container[key]
        if isinstance(item, list):
            # for simplicity if any fails, we nullify the whole list or clear it
            container[key] = []
        elif isinstance(item, dict) and "value" in item:
            item["value"] = None
        else:
            container[key] = None
