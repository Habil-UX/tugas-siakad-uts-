
import pytest

from app.utils.pdf_generator import generate_transcript_pdf


def sample_transcript():
    return {
        "nama": "Habil Pratama Yahya",
        "nim": "251635001",
        "program_studi": "Sistem Informasi",
        "program_studi_id": 1,
        "total_sks": 6,
        "total_sks_lulus": 6,
        "ipk": 3.75,
        "predikat": "Cum Laude",
        "records": [
            {
                "semester": 2,
                "kode_mk": "IF102",
                "nama_mk": "Basis Data",
                "sks": 3,
                "nilai_huruf": "A",
                "bobot": 4.0,
                "status": "LULUS"
            },
            {
                "semester": 1,
                "kode_mk": "IF101",
                "nama_mk": "Pemrograman",
                "sks": 3,
                "nilai_huruf": "B",
                "bobot": 3.0,
                "status": "LULUS"
            }
        ],
        "rekap_semester": [
            {
                "semester": 1,
                "ips": 3.0,
                "total_sks": 3,
                "total_sks_lulus": 3,
                "total_mutu": 9.0
            },
            {
                "semester": 2,
                "ips": 4.0,
                "total_sks": 3,
                "total_sks_lulus": 3,
                "total_mutu": 12.0
            }
        ]
    }


# ==========================================
# TEST PDF GENERATION
# ==========================================

def test_generate_transcript_pdf_success():

    data = sample_transcript()

    result = generate_transcript_pdf(data)

    assert isinstance(result, bytes)
    assert len(result) > 0
    assert result.startswith(b"%PDF")


def test_generate_transcript_pdf_empty_data():

    result = generate_transcript_pdf({})

    assert isinstance(result, bytes)
    assert result.startswith(b"%PDF")
    assert len(result) > 0


def test_generate_transcript_pdf_empty_records():

    data = sample_transcript()

    data["records"] = []

    result = generate_transcript_pdf(data)

    assert isinstance(result, bytes)
    assert result.startswith(b"%PDF")


def test_generate_transcript_pdf_empty_semester():

    data = sample_transcript()

    data["rekap_semester"] = []

    result = generate_transcript_pdf(data)

    assert isinstance(result, bytes)
    assert result.startswith(b"%PDF")


def test_generate_transcript_pdf_missing_program_studi():

    data = sample_transcript()

    data["program_studi"] = None

    result = generate_transcript_pdf(data)

    assert isinstance(result, bytes)
    assert result.startswith(b"%PDF")


def test_generate_transcript_pdf_special_characters():

    data = sample_transcript()

    data["nama"] = "Mahasiswa & Akademik"
    data["program_studi"] = "Sistem Informasi & Teknologi"
    data["records"][0]["nama_mk"] = "Pemrograman <Lanjut>"

    result = generate_transcript_pdf(data)

    assert isinstance(result, bytes)
    assert result.startswith(b"%PDF")


def test_generate_transcript_pdf_multiple_records():

    data = sample_transcript()

    for i in range(3, 35):
        data["records"].append({
            "semester": (i % 8) + 1,
            "kode_mk": f"IF{i:03d}",
            "nama_mk": f"Mata Kuliah {i}",
            "sks": 3,
            "nilai_huruf": "A",
            "bobot": 4.0,
            "status": "LULUS"
        })

    result = generate_transcript_pdf(data)

    assert isinstance(result, bytes)
    assert result.startswith(b"%PDF")
    assert len(result) > 1000


def test_generate_transcript_pdf_missing_optional_fields():

    data = {
        "records": [],
        "rekap_semester": [],
        "ipk": 0
    }

    result = generate_transcript_pdf(data)

    assert isinstance(result, bytes)
    assert result.startswith(b"%PDF")
