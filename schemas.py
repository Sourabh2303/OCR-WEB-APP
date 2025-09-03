from pydantic import BaseModel
from typing import List

class Health(BaseModel):
    status: str

class FileSummary(BaseModel):
    file_name: str
    pages: int
    rows: int

class ResultRow(BaseModel):
    id: int
    file_name: str
    page_number: int
    line_number: int
    line_text: str
    x: int
    y: int
    width: int
    height: int

    class Config:
        orm_mode = True

class PaginatedResults(BaseModel):
    total: int
    items: List[ResultRow]

class OCRJobResult(BaseModel):
    file_name: str
    engine: str
    pages: int
    rows_inserted: int
    message: str
