from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AttendanceQRGenerateRequest(BaseModel):
    valid_minutes: int = Field(default=15, ge=1, le=15)
    session_date: Optional[date] = None
    phase: Optional[str] = Field(default=None)
    dosen_id: Optional[int] = None
    revoke_previous: bool = True


class AttendanceScanRequest(BaseModel):
    token: str = Field(..., min_length=10)
    nim: str = Field(..., min_length=3, max_length=30)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    scan_time: Optional[datetime] = None


class AIInsightsAnalyzeRequest(BaseModel):
    attendance_records: Optional[List[dict]] = None
    schedule_id: Optional[int] = None
    matakuliah_id: Optional[int] = None
    min_sessions: int = Field(default=2, ge=1)
