from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AttendanceRecord,
    AttendanceSession,
    CalonMahasiswa,
    Dosen,
    JadwalKuliah,
    Matakuliah,
    Ruangan,
)
from app.schemas.attendance import (
    AIInsightsAnalyzeRequest,
    AttendanceQRGenerateRequest,
    AttendanceScanRequest,
)
from app.services.ai_attendance_analyzer import AIAttendanceAnalyzer
from app.services.attendance_report_service import AttendanceReportService
from app.services.attendance_service import AttendanceService
from app.utils.security import get_optional_current_user, require_roles

router = APIRouter(tags=["Attendance (QR Code)"])


def require_report_authorization(
    role: Optional[str] = Query(default=None),
    current_user: Optional[dict] = Depends(get_optional_current_user),
) -> dict:
    effective_user = current_user
    if effective_user is None and role:
        effective_user = {"role": role.lower().strip()}
    if effective_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Otorisasi diperlukan untuk mengakses laporan presensi",
        )
    user_role = str(effective_user.get("role", "")).lower()
    if user_role not in ("dosen", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak: laporan presensi hanya dapat diakses oleh Dosen atau Admin",
        )
    return effective_user


@router.get("/attendance/qr/{schedule_id}")
@router.get("/api/attendance/qr/{schedule_id}")
def get_attendance_qr_png(
    schedule_id: int,
    valid_minutes: int = Query(default=15, ge=1, le=15),
    session_date: Optional[date] = Query(default=None),
    phase: Optional[str] = Query(default=None),
    dosen_id: Optional[int] = Query(default=None),
    revoke_previous: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(require_roles(["dosen", "admin"])),
):
    svc = AttendanceService(db)
    data = svc.generate_qr(
        schedule_id=schedule_id,
        valid_minutes=valid_minutes,
        session_date=session_date,
        current_user=current_user,
        dosen_id=dosen_id,
        phase=phase,
        revoke_previous=revoke_previous,
    )
    headers = {
        "X-Attendance-Token": data["token"],
        "X-Attendance-Session-Id": str(data["session_id"]),
        "X-Attendance-Schedule-Id": str(data["schedule_id"]),
        "X-Attendance-JTI": data["jti"],
        "X-Attendance-Phase": data["phase"],
        "X-Attendance-Generated-At": data["generated_at"],
        "X-Attendance-Expires-At": data["expires_at"],
        "X-Attendance-Expires-In": str(data["expires_in_seconds"]),
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    }
    return Response(
        content=data["png_bytes"],
        media_type="image/png",
        headers=headers,
    )


@router.post("/attendance/qr/{schedule_id}/generate")
@router.post("/api/attendance/qr/{schedule_id}/generate")
def generate_attendance_qr_json(
    schedule_id: int,
    payload: Optional[AttendanceQRGenerateRequest] = None,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(require_roles(["dosen", "admin"])),
):
    req = payload or AttendanceQRGenerateRequest()
    svc = AttendanceService(db)
    data = svc.generate_qr(
        schedule_id=schedule_id,
        valid_minutes=req.valid_minutes,
        session_date=req.session_date,
        current_user=current_user,
        dosen_id=req.dosen_id,
        phase=req.phase,
        revoke_previous=req.revoke_previous,
    )
    return {
        "schedule_id": data["schedule_id"],
        "session_id": data["session_id"],
        "session_date": data["session_date"],
        "jti": data["jti"],
        "phase": data["phase"],
        "generated_at": data["generated_at"],
        "expires_at": data["expires_at"],
        "expires_in_seconds": data["expires_in_seconds"],
        "token": data["token"],
        "qr_base64": data["qr_base64"],
        "qr_image_url": f"/attendance/qr/{schedule_id}",
    }


@router.post("/attendance/scan")
@router.post("/api/attendance/scan")
def scan_attendance_qr(
    payload: AttendanceScanRequest,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    svc = AttendanceService(db)
    return svc.scan_attendance(
        token=payload.token,
        nim=payload.nim,
        current_user=current_user,
        scan_time=payload.scan_time,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )


@router.get("/attendance/session/{session_id}/records")
@router.get("/api/attendance/session/{session_id}/records")
def get_session_attendance_records(
    session_id: int,
    db: Session = Depends(get_db),
):
    session = (
        db.query(AttendanceSession)
        .filter(AttendanceSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesi presensi tidak ditemukan",
        )
    records = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.session_id == session.id)
        .order_by(AttendanceRecord.scanned_at.asc())
        .all()
    )
    items = []
    for r in records:
        st = (
            db.query(CalonMahasiswa)
            .filter(CalonMahasiswa.id == r.student_id)
            .first()
        )
        items.append(
            {
                "id": r.id,
                "nim": r.nim,
                "nama_mahasiswa": st.nama_lengkap if st else r.nim,
                "scanned_at": r.scanned_at.isoformat(),
                "attendance_status": r.attendance_status,
                "qr_token_id": r.qr_token_id,
            }
        )
    return {
        "session_id": session.id,
        "schedule_id": session.schedule_id,
        "session_date": str(session.session_date),
        "session_status": session.session_status,
        "total_present": len(items),
        "records": items,
    }


@router.post("/attendance/session/{session_id}/close")
@router.post("/api/attendance/session/{session_id}/close")
def close_attendance_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(require_roles(["dosen", "admin"])),
):
    session = (
        db.query(AttendanceSession)
        .filter(AttendanceSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesi presensi tidak ditemukan",
        )
    session.session_status = "CLOSED"
    db.commit()
    return {
        "session_id": session.id,
        "session_status": session.session_status,
        "message": "Sesi presensi telah ditutup",
    }


@router.get("/attendance/report")
@router.get("/api/attendance/report")
def get_attendance_report(
    schedule_id: Optional[int] = Query(default=None),
    matakuliah_id: Optional[int] = Query(default=None),
    nim: Optional[str] = Query(default=None),
    reference_time: Optional[datetime] = Query(default=None),
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_report_authorization),
):
    report_svc = AttendanceReportService(db)
    return report_svc.get_attendance_report(
        schedule_id=schedule_id,
        matakuliah_id=matakuliah_id,
        nim=nim,
        reference_time=reference_time,
    )


@router.get("/attendance/report/export")
@router.get("/api/attendance/report/export")
def export_attendance_report_excel(
    schedule_id: Optional[int] = Query(default=None),
    matakuliah_id: Optional[int] = Query(default=None),
    nim: Optional[str] = Query(default=None),
    reference_time: Optional[datetime] = Query(default=None),
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_report_authorization),
):
    report_svc = AttendanceReportService(db)
    excel_bytes = report_svc.export_excel_bytes(
        schedule_id=schedule_id,
        matakuliah_id=matakuliah_id,
        nim=nim,
        reference_time=reference_time,
    )
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="laporan_presensi_mahasiswa.xlsx"'
        },
    )


@router.get("/attendance/ai-insights")
@router.get("/api/attendance/ai-insights")
def get_ai_attendance_insights(
    schedule_id: Optional[int] = Query(default=None),
    matakuliah_id: Optional[int] = Query(default=None),
    min_sessions: int = Query(default=2, ge=1),
    reference_time: Optional[datetime] = Query(default=None),
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_report_authorization),
):
    analyzer = AIAttendanceAnalyzer(db)
    return analyzer.analyze_from_db(
        schedule_id=schedule_id,
        matakuliah_id=matakuliah_id,
        min_sessions=min_sessions,
        reference_time=reference_time,
    )


@router.post("/attendance/ai-insights")
@router.post("/api/attendance/ai-insights")
def post_ai_attendance_insights(
    payload: AIInsightsAnalyzeRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_report_authorization),
):
    analyzer = AIAttendanceAnalyzer(db)
    return analyzer.analyze(
        attendance_records=payload.attendance_records,
        schedule_id=payload.schedule_id,
        matakuliah_id=payload.matakuliah_id,
        min_sessions=payload.min_sessions,
    )


@router.get("/attendance-ui", response_class=HTMLResponse)
def attendance_management_ui():
    return """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Manajemen Presensi QR Code & AI Attendance Insights — SIAKAD</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f7fb; color: #1e293b; }
        .nav { margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap; }
        .nav a { background: #263B5E; color: #fff; text-decoration: none; padding: 8px 14px; border-radius: 6px; font-size: 14px; }
        .nav a.active { background: #2563eb; font-weight: 600; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 20px; }
        .card { background: #fff; border-radius: 10px; padding: 18px; margin-bottom: 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.07); }
        h1 { margin-top: 0; font-size: 24px; color: #0f172a; }
        h2 { margin-top: 0; font-size: 18px; color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }
        label { display: block; margin-top: 10px; font-weight: 600; font-size: 13px; color: #334155; }
        input, select, textarea { width: 100%; padding: 8px 10px; margin-top: 4px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; }
        .btn-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
        button { background: #2563eb; color: #fff; border: none; padding: 9px 14px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px; }
        button.secondary { background: #0f766e; }
        button.warning { background: #d97706; }
        button.danger { background: #dc2626; }
        .qr-box { text-align: center; margin-top: 14px; padding: 14px; background: #f8fafc; border: 1px dashed #94a3b8; border-radius: 8px; }
        .qr-box img { width: 240px; height: 240px; object-fit: contain; border: 4px solid #fff; box-shadow: 0 1px 4px rgba(0,0,0,0.12); }
        .countdown { font-size: 22px; font-weight: 700; color: #dc2626; margin: 8px 0; }
        .badge-warn { background: #fee2e2; color: #991b1b; padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 12px; }
        .badge-ok { background: #dcfce7; color: #166534; padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 12px; }
        .status-box { margin-top: 12px; padding: 12px; border-radius: 6px; font-weight: 600; display: none; }
        .status-ok { background: #dcfce7; color: #166534; border: 1px solid #86efac; display: block; }
        .status-err { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; display: block; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #cbd5e1; padding: 8px; text-align: left; font-size: 13px; }
        th { background: #263B5E; color: #fff; }
        video { width: 100%; max-width: 320px; border-radius: 8px; background: #000; display: none; margin: 10px auto; }
        @media (max-width: 600px) { body { padding: 12px; } .qr-box img { width: 200px; height: 200px; } }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/dashboard">Conflict Resolver Jadwal</a>
        <a href="/grades-ui">Form Input & Edit Nilai</a>
        <a href="/finance-dashboard">Dashboard Keuangan SPP</a>
        <a href="/attendance-ui" class="active">Presensi QR Code (Minggu 12)</a>
        <a href="/docs">Swagger API Docs</a>
    </div>

    <h1>Sistem Presensi Mahasiswa Berbasis QR Code & AI Attendance Insights</h1>

    <div class="grid">
        <!-- PANEL DOSEN: GENERATE QR & COUNTDOWN -->
        <div class="card">
            <h2>Panel Dosen — Generate QR Code Sesi Kuliah</h2>
            <label for="sched_select">Pilih Jadwal Kuliah Aktif</label>
            <select id="sched_select"></select>

            <label for="valid_min">Masa Berlaku QR (Maksimal 15 Menit)</label>
            <input id="valid_min" type="number" min="1" max="15" value="15">

            <div class="btn-row">
                <button onclick="generateQR('NORMAL')">Generate QR (Periode Normal 0–15m)</button>
                <button class="warning" onclick="generateQR('LATE')">Re-Generate QR (Periode Terlambat 15–30m)</button>
            </div>

            <div class="qr-box" id="qr_container" style="display:none;">
                <div id="qr_phase_label" style="font-weight:700;color:#1e3a8a;"></div>
                <div class="countdown" id="qr_countdown">15:00</div>
                <img id="qr_img" alt="QR Code Presensi" src="">
                <div style="font-size:12px;color:#475569;margin-top:6px;">
                    Session ID: <span id="qr_session_id">-</span> | JTI: <span id="qr_jti">-</span>
                </div>
                <div class="btn-row" style="justify-content:center;">
                    <button class="secondary" onclick="copyActiveTokenToScanner()">Salin Token ke Form Scan Mahasiswa</button>
                    <button class="danger" onclick="closeCurrentSession()">Akhiri / Tutup Sesi</button>
                </div>
            </div>

            <h3 style="font-size:15px;margin-top:16px;">Daftar Mahasiswa Hadir pada Sesi Ini</h3>
            <table>
                <thead><tr><th>NIM</th><th>Nama Mahasiswa</th><th>Waktu Scan</th><th>Status</th></tr></thead>
                <tbody id="session_records_body">
                    <tr><td colspan="4">Belum ada sesi dipilih.</td></tr>
                </tbody>
            </table>
        </div>

        <!-- PANEL MAHASISWA: SCAN QR KAMERA / MANUAL FALLBACK -->
        <div class="card">
            <h2>Panel Mahasiswa — Scan QR Code Presensi</h2>
            <label for="scan_nim">NIM Mahasiswa</label>
            <input id="scan_nim" placeholder="Contoh: 2026110001" value="2026110001">

            <div class="btn-row">
                <button onclick="startCameraScanner()">Buka Kamera QR Scanner</button>
                <button class="danger" id="stop_cam_btn" onclick="stopCameraScanner()" style="display:none;">Matikan Kamera</button>
            </div>
            <video id="qr_video" playsinline></video>
            <div id="cam_hint" style="font-size:12px;color:#64748b;margin-top:4px;"></div>

            <label for="scan_token">Token JWT QR Presensi (Otomatis dari Kamera atau Input Manual Fallback)</label>
            <textarea id="scan_token" rows="3" placeholder="Tempelkan token JWT dari QR Code di sini..."></textarea>

            <div class="btn-row">
                <button class="secondary" onclick="submitAttendanceScan()">Kirim Presensi Sekarang</button>
            </div>

            <div id="scan_result_box" class="status-box"></div>
        </div>
    </div>

    <!-- PANEL LAPORAN PRESENSI, WARNING <75% & EXPORT EXCEL -->
    <div class="card">
        <h2>Laporan Presensi Mahasiswa & Indikator Warning (&lt;75%)</h2>
        <div class="btn-row" style="margin-bottom:10px;">
            <button onclick="loadAttendanceReport()">Refresh Laporan Presensi</button>
            <button class="secondary" onclick="downloadExcelReport()">Export Laporan ke Excel (.xlsx)</button>
            <button class="warning" onclick="loadAIInsights()">Muat Analisis AI Attendance Insights</button>
        </div>
        <div id="report_summary" style="font-weight:600;margin-bottom:8px;"></div>
        <table>
            <thead>
                <tr>
                    <th>NIM</th>
                    <th>Nama Mahasiswa</th>
                    <th>Mata Kuliah</th>
                    <th>Total Sesi Berlangsung</th>
                    <th>Hadir</th>
                    <th>Terlambat</th>
                    <th>Tidak Hadir</th>
                    <th>Persentase (%)</th>
                    <th>Status Warning</th>
                </tr>
            </thead>
            <tbody id="report_body"></tbody>
        </table>
    </div>

    <!-- PANEL AI ATTENDANCE INSIGHTS -->
    <div class="card">
        <h2>AI Attendance Insights — Deteksi Pola Absensi & Rekomendasi Tindakan</h2>
        <div id="ai_early_warning" style="font-weight:700;color:#b91c1c;margin-bottom:10px;"></div>
        <div class="grid">
            <div>
                <h3 style="font-size:15px;">Pola Ketidakhadiran Terdeteksi (Insights)</h3>
                <ul id="ai_insights_list"></ul>
            </div>
            <div>
                <h3 style="font-size:15px;">Rekomendasi Tindakan Prioritas (Actions)</h3>
                <ul id="ai_actions_list"></ul>
            </div>
        </div>
    </div>

    <script>
        let activeToken = '';
        let activeSessionId = null;
        let countdownTimer = null;
        let remainingSeconds = 0;
        let mediaStream = null;
        let scanInterval = null;

        async function loadSchedules() {
            const res = await fetch('/api/schedules');
            const list = await res.json();
            const sel = document.getElementById('sched_select');
            sel.innerHTML = '';
            (list || []).forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.id;
                opt.textContent = `Jadwal #${s.id} — MK ID ${s.matakuliah_id} (${s.hari}, ${s.jam_mulai} - ${s.jam_selesai})`;
                sel.appendChild(opt);
            });
        }

        async function generateQR(phase) {
            const schedId = document.getElementById('sched_select').value;
            const validMin = parseInt(document.getElementById('valid_min').value || '15');
            if (!schedId) return;

            const res = await fetch(`/attendance/qr/${schedId}/generate`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-User-Role': 'dosen'},
                body: JSON.stringify({valid_minutes: validMin, phase: phase, revoke_previous: true})
            });
            const data = await res.json();
            if (!res.ok) {
                alert('Gagal membuat QR: ' + JSON.stringify(data.detail));
                return;
            }
            activeToken = data.token;
            activeSessionId = data.session_id;
            remainingSeconds = data.expires_in_seconds;

            document.getElementById('qr_container').style.display = 'block';
            document.getElementById('qr_phase_label').innerText = `Fase QR: ${data.phase} (Jadwal #${data.schedule_id})`;
            document.getElementById('qr_img').src = data.qr_base64;
            document.getElementById('qr_session_id').innerText = data.session_id;
            document.getElementById('qr_jti').innerText = data.jti.substring(0, 12) + '...';

            startCountdown();
            loadSessionRecords(activeSessionId);
        }

        function startCountdown() {
            if (countdownTimer) clearInterval(countdownTimer);
            updateCountdownDisplay();
            countdownTimer = setInterval(() => {
                remainingSeconds = Math.max(0, remainingSeconds - 1);
                updateCountdownDisplay();
                if (remainingSeconds <= 0) {
                    clearInterval(countdownTimer);
                }
            }, 1000);
        }

        function updateCountdownDisplay() {
            const mins = String(Math.floor(remainingSeconds / 60)).padStart(2, '0');
            const secs = String(remainingSeconds % 60).padStart(2, '0');
            const el = document.getElementById('qr_countdown');
            el.innerText = remainingSeconds > 0 ? `Berlaku: ${mins}:${secs}` : 'QR KEDALUWARSA (EXPIRED)';
        }

        function copyActiveTokenToScanner() {
            document.getElementById('scan_token').value = activeToken;
        }

        async function closeCurrentSession() {
            if (!activeSessionId) return;
            await fetch(`/attendance/session/${activeSessionId}/close`, {
                method: 'POST',
                headers: {'X-User-Role': 'dosen'}
            });
            await loadAttendanceReport();
            await loadAIInsights();
        }

        async function loadSessionRecords(sessionId) {
            if (!sessionId) return;
            const res = await fetch(`/attendance/session/${sessionId}/records`);
            if (!res.ok) return;
            const data = await res.json();
            const tbody = document.getElementById('session_records_body');
            tbody.innerHTML = '';
            if (!data.records || data.records.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4">Belum ada mahasiswa yang scan pada sesi ini.</td></tr>';
                return;
            }
            data.records.forEach(r => {
                const badge = r.attendance_status === 'HADIR'
                    ? '<span class="badge-ok">HADIR</span>'
                    : '<span class="badge-warn">TERLAMBAT</span>';
                tbody.innerHTML += `<tr>
                    <td>${r.nim}</td>
                    <td>${r.nama_mahasiswa}</td>
                    <td>${r.scanned_at}</td>
                    <td>${badge}</td>
                </tr>`;
            });
        }

        async function startCameraScanner() {
            const video = document.getElementById('qr_video');
            const hint = document.getElementById('cam_hint');
            const stopBtn = document.getElementById('stop_cam_btn');
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                hint.innerText = 'Kamera tidak tersedia pada perangkat/browser ini. Gunakan input token manual di bawah.';
                return;
            }
            try {
                mediaStream = await navigator.mediaDevices.getUserMedia({video: {facingMode: 'environment'}});
                video.srcObject = mediaStream;
                video.style.display = 'block';
                stopBtn.style.display = 'inline-block';
                await video.play();
                hint.innerText = 'Arahkan kamera ke QR Code Dosen...';

                if ('BarcodeDetector' in window) {
                    const detector = new BarcodeDetector({formats: ['qr_code']});
                    scanInterval = setInterval(async () => {
                        try {
                            const codes = await detector.detect(video);
                            if (codes.length > 0 && codes[0].rawValue) {
                                document.getElementById('scan_token').value = codes[0].rawValue;
                                stopCameraScanner();
                                await submitAttendanceScan();
                            }
                        } catch (_) {}
                    }, 500);
                } else {
                    hint.innerText = 'Kamera aktif. Jika browser belum mendukung BarcodeDetector native, gunakan tombol Salin Token / Input Manual.';
                }
            } catch (err) {
                hint.innerText = 'Akses kamera ditolak atau tidak ditemukan. Silakan gunakan input token manual.';
            }
        }

        function stopCameraScanner() {
            if (scanInterval) clearInterval(scanInterval);
            if (mediaStream) {
                mediaStream.getTracks().forEach(t => t.stop());
                mediaStream = null;
            }
            document.getElementById('qr_video').style.display = 'none';
            document.getElementById('stop_cam_btn').style.display = 'none';
        }

        async function submitAttendanceScan() {
            const nim = document.getElementById('scan_nim').value.trim();
            const token = document.getElementById('scan_token').value.trim();
            const box = document.getElementById('scan_result_box');

            const res = await fetch('/attendance/scan', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({nim: nim, token: token})
            });
            const data = await res.json();
            if (res.ok) {
                box.className = 'status-box status-ok';
                box.innerText = `BERHASIL [${data.attendance_status}]: ${data.message} — ${data.nama_mahasiswa} (${data.kode_mk})`;
                if (activeSessionId) await loadSessionRecords(activeSessionId);
            } else {
                box.className = 'status-box status-err';
                box.innerText = `GAGAL (${res.status}): ${data.detail}`;
            }
        }

        async function loadAttendanceReport() {
            const res = await fetch('/attendance/report?role=dosen', {
                headers: {'X-User-Role': 'dosen'}
            });
            const data = await res.json();
            if (!res.ok) return;
            document.getElementById('report_summary').innerText =
                `Total Baris Laporan: ${data.total_rows} | Mahasiswa Warning (<75%): ${data.total_warning_count}`;
            const tbody = document.getElementById('report_body');
            tbody.innerHTML = '';
            if (!data.records || data.records.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9">Belum ada data laporan presensi.</td></tr>';
                return;
            }
            data.records.forEach(r => {
                const badge = r.is_warning
                    ? `<span class="badge-warn">${r.status_warning}</span>`
                    : `<span class="badge-ok">${r.status_warning}</span>`;
                tbody.innerHTML += `<tr>
                    <td>${r.nim}</td>
                    <td>${r.nama_mahasiswa}</td>
                    <td>${r.kode_mk} - ${r.nama_mk}</td>
                    <td>${r.total_sesi_berlangsung}</td>
                    <td>${r.jumlah_hadir}</td>
                    <td>${r.jumlah_terlambat}</td>
                    <td>${r.jumlah_tidak_hadir}</td>
                    <td>${r.persentase_kehadiran}%</td>
                    <td>${badge}</td>
                </tr>`;
            });
        }

        function downloadExcelReport() {
            window.open('/attendance/report/export?role=dosen', '_blank');
        }

        async function loadAIInsights() {
            const res = await fetch('/attendance/ai-insights?role=dosen', {
                headers: {'X-User-Role': 'dosen'}
            });
            const data = await res.json();
            if (!res.ok) return;
            document.getElementById('ai_early_warning').innerText =
                data.summary ? data.summary.early_warning : '';

            const iList = document.getElementById('ai_insights_list');
            iList.innerHTML = '';
            if (!data.insights || data.insights.length === 0) {
                iList.innerHTML = '<li>Belum ada pola absensi berisiko yang terdeteksi.</li>';
            } else {
                data.insights.forEach(ins => {
                    iList.innerHTML += `<li><strong>[${ins.type}]</strong> ${ins.pattern} <code>${JSON.stringify(ins.evidence)}</code></li>`;
                });
            }

            const aList = document.getElementById('ai_actions_list');
            aList.innerHTML = '';
            if (!data.actions || data.actions.length === 0) {
                aList.innerHTML = '<li>Tidak ada tindakan darurat yang diperlukan saat ini.</li>';
            } else {
                data.actions.forEach(act => {
                    aList.innerHTML += `<li><strong>[${act.priority.toUpperCase()}]</strong> ${act.recommendation}</li>`;
                });
            }
        }

        loadSchedules();
        loadAttendanceReport();
        loadAIInsights();
    </script>
</body>
</html>"""
