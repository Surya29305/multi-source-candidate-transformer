from typing import Dict, Any, Optional, List
from models import CanonicalCandidate, FieldValue

class SchemaProjector:
    def project(self, candidate: CanonicalCandidate, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Projects a CanonicalCandidate into a custom structured dictionary based
        on the runtime config settings.
        """
        fields_config = config.get("fields", {})
        include_confidence = config.get("include_confidence", True)
        include_provenance = config.get("include_provenance", True)
        missing_policy = config.get("missing_field_policy", "null")
        
        output = {}
        
        for canonical_path, field_cfg in fields_config.items():
            # Get rename and path mappings
            rename_to = field_cfg.get("rename", canonical_path)
            source_path = field_cfg.get("path", canonical_path)
            
            # Fetch the field value from canonical model
            field_val = getattr(candidate, source_path, None)
            
            if field_val is None or (isinstance(field_val, list) and not field_val):
                # Handle missing/empty fields
                if missing_policy == "error":
                    raise ValueError(f"Required field '{source_path}' is missing on the candidate.")
                elif missing_policy == "omit":
                    continue
                else: # "null" policy
                    self._set_nested_value(output, rename_to, None)
            else:
                # Format the field value according to metadata configuration
                formatted_val = self._format_field(field_val, include_confidence, include_provenance)
                self._set_nested_value(output, rename_to, formatted_val)
                
        # Append overall confidence if confidence metadata is enabled
        if include_confidence:
            output["overall_confidence"] = candidate.calculate_overall_confidence()
            
        return output
        
    def _format_field(self, field_val: Any, include_conf: bool, include_prov: bool) -> Any:
        """
        Formats a FieldValue wrapper (or List of FieldValues) into raw values 
        or annotated metadata dictionaries.
        """
        if isinstance(field_val, list):
            # List fields (skills, education, experience)
            return [self._format_single_value(item, include_conf, include_prov) for item in field_val]
        else:
            # Single fields
            return self._format_single_value(field_val, include_conf, include_prov)
            
    def _format_single_value(self, item: FieldValue, include_conf: bool, include_prov: bool) -> Any:
        # Determine if value is a Pydantic model itself (like EducationCanonical or ExperienceCanonical)
        val = item.value
        if hasattr(val, "dict"):
            val = val.dict()
            
        # If neither confidence nor provenance are requested, return clean raw value
        if not include_conf and not include_prov:
            return val
            
        # Build annotated dictionary representation
        result = {"value": val}
        if include_conf:
            result["confidence"] = item.confidence
        if include_prov:
            result["provenance"] = [p.dict() for p in item.provenance]
            
        return result
        
    def _set_nested_value(self, d: dict, path: str, val: Any) -> None:
        """
        Sets a value in a nested dictionary using dot notation (e.g. "info.name")
        """
        parts = path.split(".")
        current = d
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = val
