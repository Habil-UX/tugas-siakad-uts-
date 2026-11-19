import pytest
from app.models import CalonMahasiswa

def get_valid_payload():
    return {
        "nama_lengkap": "Budi Santoso",
        "email": "budi@example.com",
        "phone": "081234567890",
        "tanggal_lahir": "2000-01-01",
        "alamat": "Jl. Merdeka No. 10, Jakarta",
        "program_studi_id": 1,
        "jalur_masuk_id": 1
    }

def test_register_success(client, db_session):
    payload = get_valid_payload()
    response = client.post("/api/pmb/register", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "budi@example.com"
    assert data["status"] == "pending"
    assert data["nim"] is None
    
    db_record = db_session.query(CalonMahasiswa).filter_by(email="budi@example.com").first()
    assert db_record is not None
    assert db_record.status.value == "pending"

def test_register_duplicate_email(client):
    payload = get_valid_payload()
    client.post("/api/pmb/register", json=payload) # Daftar pertama
    
    response = client.post("/api/pmb/register", json=payload) # Daftar kedua
    assert response.status_code == 409
    assert response.json()["detail"] == "Email sudah terdaftar."

def test_invalid_email(client):
    payload = get_valid_payload()
    payload["email"] = "invalid-email-format"
    response = client.post("/api/pmb/register", json=payload)
    assert response.status_code == 400

def test_invalid_phone_format(client):
    payload = get_valid_payload()
    payload["phone"] = "12345" # Bukan format Indonesia
    response = client.post("/api/pmb/register", json=payload)
    assert response.status_code == 400
    assert "Nomor telepon harus format Indonesia" in response.text

def test_invalid_program_studi(client):
    payload = get_valid_payload()
    payload["program_studi_id"] = 99 # Tidak ada di DB
    response = client.post("/api/pmb/register", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Program studi tidak ditemukan."

def test_invalid_jalur_masuk(client):
    payload = get_valid_payload()
    payload["jalur_masuk_id"] = 99 # Tidak ada di DB
    response = client.post("/api/pmb/register", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Jalur masuk tidak ditemukan."

def test_initial_registration_status(client):
    payload = get_valid_payload()
    response = client.post("/api/pmb/register", json=payload)
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
