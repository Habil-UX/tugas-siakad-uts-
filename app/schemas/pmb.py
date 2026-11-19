from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from datetime import date, datetime
import re
from typing import Optional
from app.models.calon_mahasiswa import StatusPendaftaran

class CalonMahasiswaCreate(BaseModel):
    nama_lengkap: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    phone: str
    tanggal_lahir: date
    alamat: str = Field(..., min_length=5)
    program_studi_id: int
    jalur_masuk_id: int

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower()

    @field_validator("phone")
    @classmethod
    def validate_indonesian_phone(cls, v: str) -> str:
        # Regex untuk nomor Indonesia (08... atau +628...)
        pattern = re.compile(r"^(\+62|62|0)8[1-9][0-9]{6,11}$")
        if not pattern.match(v):
            raise ValueError("Nomor telepon harus format Indonesia yang valid (contoh: 081234567890 atau +6281234567890)")
        return v

class CalonMahasiswaResponse(BaseModel):
    id: int
    nama_lengkap: str
    email: EmailStr
    phone: str
    status: StatusPendaftaran
    nim: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

from typing import List, Dict

class StatusResponse(BaseModel):
    id: int
    nama_lengkap: str
    email: EmailStr
    program_studi: str
    jalur_masuk: str
    status: StatusPendaftaran
    nim: Optional[str]
    created_at: datetime
    approved_at: Optional[datetime]

class StatsResponse(BaseModel):
    total_pendaftar: int
    status_pending: int
    status_approved: int
    status_rejected: int
    pendaftar_per_prodi: Dict[str, int]
    pendaftar_per_jalur: Dict[str, int]