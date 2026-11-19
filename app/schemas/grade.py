
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class GradeCreate(BaseModel):
    nim: str
    matakuliah_id: int
    semester: int = Field(ge=1)
    nilai_huruf: str = Field(
        pattern="^(A|B|C|D|E)$"
    )
    presensi_persen: float = Field(
        ge=0,
        le=100
    )
    changed_by: str = Field(min_length=1)
    

class GradeUpdate(BaseModel):
    nilai_huruf: str = Field(
        pattern="^(A|B|C|D|E)$"
    )
    changed_by: str = Field(min_length=1)
    reason: str = Field(min_length=5)


class GradeResponse(BaseModel):
    id: int
    nim: str
    matakuliah_id: int
    semester: int
    nilai_huruf: str
    bobot: float
    presensi_persen: float

    class Config:
        from_attributes = True


class GradeHistoryResponse(BaseModel):
    id: int
    grade_id: int
    old_value: str
    new_value: str
    changed_by: str
    changed_at: datetime
    reason: str

    class Config:
        from_attributes = True
