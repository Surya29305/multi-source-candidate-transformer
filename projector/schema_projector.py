import datetime
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
        include_metadata = config.get("include_metadata", True)
        missing_policy = config.get("missing_field_policy", "null")
        
        output = {}
        
        for canonical_path, field_cfg in fields_config.items():
            rename_to = field_cfg.get("rename", canonical_path)
            source_path = field_cfg.get("path", canonical_path)
            
            field_val = getattr(candidate, source_path, None)
            
            if field_val is None or (isinstance(field_val, list) and not field_val):
                if missing_policy == "error":
                    raise ValueError(f"Required field '{source_path}' is missing on the candidate.")
                elif missing_policy == "omit":
                    continue
                else:
                    self._set_nested_value(output, rename_to, None)
            else:
                formatted_val = self._format_field(field_val, include_confidence, include_provenance)
                self._set_nested_value(output, rename_to, formatted_val)
                
        if include_confidence:
            output["overall_confidence"] = candidate.calculate_overall_confidence()
            
        if include_metadata:
            # Dynamically collect actual raw sources processed from candidate provenance
            sources_found = set()
            model_fields = getattr(type(candidate), "model_fields", None)
            fields_to_iter = list(model_fields.keys()) if model_fields else list(candidate.__fields__)
            for k in fields_to_iter:
                field_val = getattr(candidate, k, None)
                if not field_val:
                    continue
                if isinstance(field_val, list):
                    for item in field_val:
                        if hasattr(item, "provenance"):
                            for prov in item.provenance:
                                sources_found.add(prov.source.lower())
                elif hasattr(field_val, "provenance"):
                    for prov in field_val.provenance:
                        sources_found.add(prov.source.lower())
            
            allowed_sources = {"ats", "csv", "resume", "linkedin"}
            sources_processed = sorted(list(sources_found.intersection(allowed_sources)))
            
            output["metadata"] = {
                "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                "pipeline_version": "1.2.0",
                "merge_strategy": "deterministic_priority_with_confidence_fallback",
                "confidence_strategy": "Base: ATS=0.9, CSV=0.85, Resume=0.8/0.6, LinkedIn=0.8/0.6. Matches boost to 1.0. Conflicts penalize higher score by 0.1.",
                "sources_processed": sources_processed
            }
            
        return output
        
    def _format_field(self, field_val: Any, include_conf: bool, include_prov: bool) -> Any:
        if isinstance(field_val, list):
            return [self._format_single_value(item, include_conf, include_prov) for item in field_val]
        else:
            return self._format_single_value(field_val, include_conf, include_prov)
            
    def _format_single_value(self, item: FieldValue, include_conf: bool, include_prov: bool) -> Any:
        val = item.value
        if hasattr(val, "dict"):
            val = val.dict()
            
        if not include_conf and not include_prov:
            return val
            
        result = {"value": val}
        if include_conf:
            result["confidence"] = item.confidence
        if include_prov:
            result["provenance"] = [p.dict() for p in item.provenance]
            
        return result
        
    def _set_nested_value(self, d: dict, path: str, val: Any) -> None:
        parts = path.split(".")
        current = d
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = val
