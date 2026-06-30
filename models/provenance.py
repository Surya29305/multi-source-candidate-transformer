from typing import TypeVar, Generic, List
from pydantic import BaseModel

T = TypeVar('T')

class Provenance(BaseModel):
    field: str
    source: str
    extraction_method: str

class FieldValue(BaseModel, Generic[T]):
    value: T
    confidence: float
    provenance: List[Provenance]
