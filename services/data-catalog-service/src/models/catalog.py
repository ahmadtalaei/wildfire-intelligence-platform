"""Catalog models"""
from pydantic import BaseModel

class Dataset(BaseModel):
    name: str = "sample"

class DatasetSearch(BaseModel):
    query: str = ""

class DataLineage(BaseModel):
    id: str = "lineage"

class DataQualityReport(BaseModel):
    score: float = 1.0