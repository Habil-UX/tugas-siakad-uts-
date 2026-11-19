
import app.routers.grades as grades_module


# ==========================================
# HELPER MOCK SERVICE
# ==========================================

class FakeGradeService:

    def __init__(self, db):
        self.db = db

    def input_grade(self, data):
        return {
            "message": "Nilai berhasil disimpan",
            "grade_id": 1,
            "nim": data.nim
        }

    def update_grade(
        self,
        grade_id,
        nilai_huruf,
        changed_by,
        reason
    ):
        return {
            "message": "Nilai berhasil diperbarui",
            "grade_id": grade_id,
            "old_value": "B",
            "new_value": nilai_huruf,
            "changed_by": changed_by
        }

    def get_grade_history(self, nim):
        return [
            {
                "id": 1,
                "grade_id": 1,
                "old_value": "B",
                "new_value": "A",
                "changed_by": "admin",
                "changed_at": "2026-11-11",
                "reason": "Koreksi nilai"
            }
        ]


class FakeTranscriptService:

    def __init__(self, db):
        self.db = db

    def get_ips(self, nim, semester):
        return {
            "nim": nim,
            "semester": semester,
            "ips": 3.75
        }

    def get_ipk(self, nim):
        return {
            "nim": nim,
            "ipk": 3.80
        }

    def get_transcript(self, nim):
        return {
            "nim": nim,
            "nama": "Mahasiswa Test",
            "ipk": 3.80,
            "records": []
        }


# ==========================================
# TEST INPUT GRADE
# ==========================================

def test_input_grade_router(client, monkeypatch):

    monkeypatch.setattr(
        grades_module,
        "GradeService",
        FakeGradeService
    )

    response = client.post(
        "/api/grades/input",
        json={
            "nim": "12345678",
            "matakuliah_id": 1,
            "semester": 1,
            "nilai_huruf": "A",
            "presensi_persen": 90,
            "changed_by": "admin"
        }
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Nilai berhasil disimpan"
    assert response.json()["grade_id"] == 1


# ==========================================
# TEST UPDATE GRADE
# ==========================================

def test_update_grade_router(client, monkeypatch):

    monkeypatch.setattr(
        grades_module,
        "GradeService",
        FakeGradeService
    )

    response = client.put(
        "/api/grades/update/1",
        json={
            "nilai_huruf": "A",
            "changed_by": "admin",
            "reason": "Koreksi nilai mahasiswa"
        }
    )

    assert response.status_code == 200
    assert response.json()["grade_id"] == 1
    assert response.json()["old_value"] == "B"
    assert response.json()["new_value"] == "A"


# ==========================================
# TEST GRADE HISTORY
# ==========================================

def test_get_grade_history_router(client, monkeypatch):

    monkeypatch.setattr(
        grades_module,
        "GradeService",
        FakeGradeService
    )

    response = client.get(
        "/api/grades/history/12345678"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["old_value"] == "B"
    assert data[0]["new_value"] == "A"
    assert data[0]["changed_by"] == "admin"


# ==========================================
# TEST IPS
# ==========================================

def test_get_ips_router(client, monkeypatch):

    monkeypatch.setattr(
        grades_module,
        "TranscriptService",
        FakeTranscriptService
    )

    response = client.get(
        "/api/grades/ips/12345678/2"
    )

    assert response.status_code == 200
    assert response.json()["nim"] == "12345678"
    assert response.json()["semester"] == 2
    assert response.json()["ips"] == 3.75


# ==========================================
# TEST IPK
# ==========================================

def test_get_ipk_router(client, monkeypatch):

    monkeypatch.setattr(
        grades_module,
        "TranscriptService",
        FakeTranscriptService
    )

    response = client.get(
        "/api/grades/ipk/12345678"
    )

    assert response.status_code == 200
    assert response.json()["nim"] == "12345678"
    assert response.json()["ipk"] == 3.80


# ==========================================
# TEST TRANSCRIPT JSON
# ==========================================

def test_get_transcript_router(client, monkeypatch):

    monkeypatch.setattr(
        grades_module,
        "TranscriptService",
        FakeTranscriptService
    )

    response = client.get(
        "/api/grades/transcript/12345678"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["nim"] == "12345678"
    assert data["nama"] == "Mahasiswa Test"
    assert data["ipk"] == 3.80
    assert data["records"] == []


# ==========================================
# TEST DOWNLOAD TRANSCRIPT PDF
# ==========================================

def test_download_transcript_pdf_router(
    client,
    monkeypatch
):

    monkeypatch.setattr(
        grades_module,
        "TranscriptService",
        FakeTranscriptService
    )

    monkeypatch.setattr(
        grades_module,
        "generate_transcript_pdf",
        lambda transcript: b"%PDF-1.4 test PDF content"
    )

    response = client.get(
        "/api/grades/transcript/12345678/pdf"
    )

    assert response.status_code == 200

    assert response.headers["content-type"] == "application/pdf"

    assert "transkrip_12345678.pdf" in (
        response.headers["content-disposition"]
    )

    assert response.content.startswith(b"%PDF")
