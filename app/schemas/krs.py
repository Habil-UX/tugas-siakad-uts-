from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CourseAction(BaseModel):
    nim: str
    kode_mk: str


class KRSResponse(BaseModel):
    message: str
    total_sks: int


class MKRecommendation(BaseModel):
    kode_mk: str
    nama_mk: str
    jenis_mk: str
    sks: int
    hari: str
    jam_mulai: str
    jam_selesai: str


class RecommendationResponse(BaseModel):
    nim: str
    total_sks: int
    rekomendasi_mk: List[MKRecommendation]
    wajib_terpilih: List[str]
    pilihan_terpilih: List[str]
    alasan_tidak_terpilih: Dict[str, str]


class KRSActorRequest(BaseModel):
    nidn_dosen_pa: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=20,
    )
    dosen_pa_id: Optional[int] = Field(
        default=None,
        ge=1,
    )
