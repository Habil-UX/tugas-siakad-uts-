from datetime import date, time
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import (
    CalonMahasiswa,
    Dosen,
    JadwalKuliah,
    JalurMasuk,
    KRS,
    KRSDetail,
    Matakuliah,
    ProgramStudi,
    Ruangan,
    StatusPendaftaran,
)
from app.observers import (
    AdminObserver,
    EmailChannel,
    LecturerObserver,
    Observer,
    Outbox,
    OutboxDispatcher,
    PushChannel,
    SMSChannel,
    ScheduleSubject,
    StudentObserver,
)
from app.services.krs_invalidator import KRSInvalidator
from app.services.krs_state_machine import Actor, KRSStateMachine, KRSStatus
from app.services.rescheduling_service import PROMPT_STEP_3, ReschedulingService, saring_saran
from app.utils.ics_exporter import export_student_ics, generate_ics_from_schedules

# =====================================================================
# 1. TEST 42 KOMBINASI TRANSISI ILEGAL + 6 TRANSISI LEGAL (Actor.SISTEM)
# =====================================================================

ALL_STATES = list(KRSStatus)
ALL_ACTORS = list(Actor)

LEGAL_TRIPLES = {
    (KRSStatus.DRAFT, KRSStatus.SUBMITTED, Actor.MAHASISWA),
    (KRSStatus.REVISION, KRSStatus.SUBMITTED, Actor.MAHASISWA),
    (KRSStatus.SUBMITTED, KRSStatus.APPROVED, Actor.DOSEN_PA),
    (KRSStatus.SUBMITTED, KRSStatus.REVISION, Actor.DOSEN_PA),
    (KRSStatus.SUBMITTED, KRSStatus.REVISION, Actor.SISTEM),
    (KRSStatus.APPROVED, KRSStatus.REVISION, Actor.SISTEM),
}

ILLEGAL_42_TRIPLES = [
    (s_from, s_to, act)
    for s_from in ALL_STATES
    for s_to in ALL_STATES
    for act in ALL_ACTORS
    if (s_from, s_to, act) not in LEGAL_TRIPLES
]


def test_count_illegal_triples_is_exactly_42():
    assert len(ILLEGAL_42_TRIPLES) == 42
    assert len(LEGAL_TRIPLES) == 6


@pytest.mark.parametrize("from_state,to_state,actor", ILLEGAL_42_TRIPLES)
def test_42_illegal_actor_transitions_rejected(from_state, to_state, actor):
    assert KRSStateMachine.can_transition(from_state, to_state, actor=actor) is False
    with pytest.raises(HTTPException) as exc:
        KRSStateMachine.transition(from_state, to_state, actor=actor)
    assert exc.value.status_code == 400


@pytest.mark.parametrize("from_state,to_state,actor", list(LEGAL_TRIPLES))
def test_6_legal_actor_transitions_allowed(from_state, to_state, actor):
    assert KRSStateMachine.can_transition(from_state, to_state, actor=actor) is True
    assert KRSStateMachine.transition(from_state, to_state, actor=actor) == to_state.value


# =====================================================================
# 2. TEST OBSERVER + KANAL BISA DITUKAR + TRY/EXCEPT + OUTBOX SETELAH COMMIT
# =====================================================================

class FailingObserver(Observer):
    def update(self, event_type: str, data: dict):
        raise RuntimeError("Simulasi kegagalan 1 observer")


def test_schedule_subject_try_except_and_outbox_after_commit(db_session):
    outbox = Outbox()
    subject = ScheduleSubject()

    # Pasang 1 observer yang error di awal untuk membuktikan try/except per observer
    subject.attach(FailingObserver())
    subject.attach(StudentObserver(db_session, ["2026TIF-0801"], channel=EmailChannel(), outbox=outbox))
    subject.attach(LecturerObserver(db_session, dosen_id=10, channel=SMSChannel(), outbox=outbox))
    subject.attach(AdminObserver(db_session, channel=PushChannel(), outbox=outbox))

    event_payload = {"id": 88, "nama_mk": "Pemrograman Berorientasi Objek"}
    subject.notify("SCHEDULE_UPDATED", event_payload)

    # Uji idempotency key: notifikasi kedua dengan event & jadwal sama tidak menggandakan outbox
    subject.notify("SCHEDULE_UPDATED", event_payload)
    assert len(outbox.entries) == 3
    assert len(outbox.pending_entries) == 3

    dispatcher = OutboxDispatcher(db=db_session)
    sent = dispatcher.dispatch_after_commit(outbox)
    assert len(sent) == 3
    assert all(e.status == "SENT" for e in sent)

    # Dispatch ulang tidak mengirim pesan duplikat
    sent_again = dispatcher.dispatch_after_commit(outbox)
    assert len(sent_again) == 0


# =====================================================================
# 3. TEST KRSInvalidator + Transisi Actor.SISTEM -> REVISION
# =====================================================================

def test_krs_invalidator_transitions_approved_to_revision_by_actor_sistem(db_session):
    prodi = ProgramStudi(kode="IF8", nama="Informatika W8", fakultas="FIK")
    jalur = JalurMasuk(kode="SNBP8", nama="SNBP W8")
    db_session.add_all([prodi, jalur])
    db_session.flush()

    mhs = CalonMahasiswa(
        nama_lengkap="Mahasiswa Minggu 8",
        email="mhs.w8@example.com",
        phone="081234567808",
        tanggal_lahir=date(2005, 8, 8),
        alamat="Jl. Kampus 8",
        program_studi_id=prodi.id,
        jalur_masuk_id=jalur.id,
        status=StatusPendaftaran.approved,
        nim="2026IF8-0001",
    )
    mk = Matakuliah(
        kode_mk="IF801",
        nama_mk="Arsitektur Perangkat Lunak",
        sks=3,
        semester=3,
        jenis_mk="Wajib",
        hari="Senin",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
    )
    db_session.add_all([mhs, mk])
    db_session.flush()

    krs = KRS(
        nim=mhs.nim,
        semester_akademik=3,
        tahun_akademik="2026/2027",
        total_sks=3,
        status=KRSStatus.APPROVED.value,
        needs_review=False,
    )
    db_session.add(krs)
    db_session.flush()
    db_session.add(KRSDetail(krs_id=krs.id, matakuliah_id=mk.id))
    db_session.commit()

    invalidator = KRSInvalidator(db_session)
    affected = invalidator.invalidate_by_matakuliah(mk.id, force_transition_to_revision=True)
    db_session.commit()

    assert len(affected) == 1
    assert krs.status == KRSStatus.REVISION.value
    assert krs.needs_review is True


# =====================================================================
# 4. TEST PROMPT STEP 3 + saring_saran + EKSPOR .ICS
# =====================================================================

def test_saring_saran_and_ics_export(db_session):
    assert "saring_saran" in PROMPT_STEP_3

    mk = Matakuliah(
        kode_mk="IF802",
        nama_mk="Desain Pola OOP",
        sks=3,
        semester=3,
        jenis_mk="Wajib",
        hari="Selasa",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
    )
    dosen = Dosen(nidn="88001122", nama="Dr. Budi Pengampu")
    r_kecil = Ruangan(kode_ruangan="R801", nama_ruangan="Lab Kecil", kapasitas=10, is_active=True)
    r_besar = Ruangan(kode_ruangan="R802", nama_ruangan="Aula Besar", kapasitas=50, is_active=True)
    db_session.add_all([mk, dosen, r_kecil, r_besar])
    db_session.flush()

    jadwal_asal = JadwalKuliah(
        matakuliah_id=mk.id,
        dosen_id=dosen.id,
        ruangan_id=r_besar.id,
        hari="Selasa",
        jam_mulai=time(8, 0),
        jam_selesai=time(10, 0),
        tahun_akademik="2026/2027",
        semester_akademik=3,
        status="AKTIF",
    )
    jadwal_bentrok = JadwalKuliah(
        matakuliah_id=mk.id,
        dosen_id=dosen.id,
        ruangan_id=r_besar.id,
        hari="Selasa",
        jam_mulai=time(10, 0),
        jam_selesai=time(12, 0),
        tahun_akademik="2026/2027",
        semester_akademik=3,
        status="AKTIF",
    )
    db_session.add_all([jadwal_asal, jadwal_bentrok])
    db_session.commit()

    raw_ai_suggestions = [
        # 1. Ditolak karena kapasitas R801 (10) < jumlah_mahasiswa (25)
        {"hari": "Selasa", "jam_mulai": "13:00", "jam_selesai": "15:00", "ruangan": "R801"},
        # 2. Ditolak karena bentrok dengan jadwal_bentrok (10:00-12:00 di R802)
        {"hari": "Selasa", "jam_mulai": "10:00", "jam_selesai": "12:00", "ruangan": "R802"},
        # 3. Lolos saringan karena R802 kapasitas 50 >= 25 dan jam 13:00-15:00 bebas konflik
        {"hari": "Selasa", "jam_mulai": "13:00", "jam_selesai": "15:00", "ruangan": "R802"},
    ]

    service = ReschedulingService(db_session)
    filtered = service.saring_saran(
        raw_suggestions=raw_ai_suggestions,
        jadwal_asal=jadwal_asal,
        existing_schedules=[jadwal_bentrok],
        rooms_by_code={"R801": r_kecil, "R802": r_besar},
        jumlah_mahasiswa=25,
    )
    assert len(filtered) == 1
    assert filtered[0]["ruangan"] == "R802"
    assert filtered[0]["jam"] == "13:00-15:00"

    # Uji ekspor .ics
    ics_text = generate_ics_from_schedules(db_session, [jadwal_asal])
    assert "BEGIN:VCALENDAR" in ics_text
    assert "BEGIN:VEVENT" in ics_text
    assert "IF802 - Desain Pola OOP" in ics_text

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        resp = TestClient(app).get("/api/schedules/export.ics")
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert "BEGIN:VCALENDAR" in resp.text
