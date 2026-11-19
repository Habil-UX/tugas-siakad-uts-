import pytest
from app.models import CalonMahasiswa, StatusPendaftaran, NimSequence

def create_dummy_student(client, email="test@example.com"):
    payload = {
        "nama_lengkap": "Test User",
        "email": email,
        "phone": "081234567890",
        "tanggal_lahir": "2000-01-01",
        "alamat": "Jl. Test",
        "program_studi_id": 1,
        "jalur_masuk_id": 1
    }
    response = client.post("/api/pmb/register", json=payload)
    return response.json()["id"]

# 1. test_approve_success
def test_approve_success(client):
    student_id = create_dummy_student(client)
    response = client.put(f"/api/pmb/approve/{student_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["nim"] is not None
    assert len(data["nim"]) == 12 # 4 tahun + 3 prodi + 1 strip + 4 angka

# 2. test_approve_idempotent
def test_approve_idempotent(client):
    student_id = create_dummy_student(client)
    res1 = client.put(f"/api/pmb/approve/{student_id}").json()
    res2 = client.put(f"/api/pmb/approve/{student_id}").json()
    assert res1["nim"] == res2["nim"]
    assert res2["status"] == "approved"

# 3. test_approve_invalid_id
def test_approve_invalid_id(client):
    response = client.put("/api/pmb/approve/9999")
    assert response.status_code == 404

# 4. test_approve_invalid_status (rejected to approved)
def test_approve_invalid_status(client):
    student_id = create_dummy_student(client)
    client.put(f"/api/pmb/reject/{student_id}") # Reject dulu
    response = client.put(f"/api/pmb/approve/{student_id}") # Coba approve
    assert response.status_code == 409

# 5. test_generate_nim_sequential (Format & Sequence)
def test_generate_nim_sequential(client):
    id1 = create_dummy_student(client, "a@test.com")
    id2 = create_dummy_student(client, "b@test.com")
    
    nim1 = client.put(f"/api/pmb/approve/{id1}").json()["nim"]
    nim2 = client.put(f"/api/pmb/approve/{id2}").json()["nim"]
    
    # Ekstrak running number (4 digit terakhir)
    seq1 = int(nim1[-4:])
    seq2 = int(nim2[-4:])
    assert seq2 == seq1 + 1

# 7. test_reject_success
def test_reject_success(client):
    student_id = create_dummy_student(client)
    response = client.put(f"/api/pmb/reject/{student_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["nim"] is None

# 8. test_reject_approved_student
def test_reject_approved_student(client):
    student_id = create_dummy_student(client)
    client.put(f"/api/pmb/approve/{student_id}")
    response = client.put(f"/api/pmb/reject/{student_id}")
    assert response.status_code == 409

# 9. test_get_status
def test_get_status(client):
    student_id = create_dummy_student(client)
    response = client.get(f"/api/pmb/status/{student_id}")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

# 10. test_get_status_not_found
def test_get_status_not_found(client):
    response = client.get("/api/pmb/status/9999")
    assert response.status_code == 404

# 11. test_get_stats
def test_get_stats(client):
    create_dummy_student(client, "c@test.com")
    create_dummy_student(client, "d@test.com")
    response = client.get("/api/pmb/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_pendaftar"] == 2
    assert data["status_pending"] == 2
    assert data["pendaftar_per_prodi"]["Teknik Informatika"] == 2