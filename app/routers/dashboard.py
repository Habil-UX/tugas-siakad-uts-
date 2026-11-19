from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Dosen, JadwalKuliah, Matakuliah, Ruangan
from app.services.conflict_detector import detect_all_schedule_conflicts

router = APIRouter(tags=["Dashboard"])


@router.get("/api/admin/scheduling/dashboard")
def get_scheduling_dashboard_data(db: Session = Depends(get_db)):
    schedules = db.query(JadwalKuliah).all()
    conflicts = detect_all_schedule_conflicts(schedules)

    schedule_map = {}
    detailed_schedules = []
    for s in schedules:
        mk = (
            db.query(Matakuliah)
            .filter(Matakuliah.id == s.matakuliah_id)
            .first()
        )
        dosen = db.query(Dosen).filter(Dosen.id == s.dosen_id).first()
        ruangan = db.query(Ruangan).filter(Ruangan.id == s.ruangan_id).first()
        item = {
            "id": s.id,
            "hari": s.hari,
            "jam_mulai": str(s.jam_mulai),
            "jam_selesai": str(s.jam_selesai),
            "tahun_akademik": s.tahun_akademik,
            "semester_akademik": s.semester_akademik,
            "status": s.status,
            "matakuliah": {
                "id": mk.id if mk else s.matakuliah_id,
                "kode_mk": mk.kode_mk if mk else "-",
                "nama_mk": mk.nama_mk if mk else "-",
            },
            "dosen": {
                "id": dosen.id if dosen else s.dosen_id,
                "nidn": dosen.nidn if dosen else "-",
                "nama": dosen.nama if dosen else "-",
            },
            "ruangan": {
                "id": ruangan.id if ruangan else s.ruangan_id,
                "kode_ruangan": ruangan.kode_ruangan if ruangan else "-",
                "nama_ruangan": ruangan.nama_ruangan if ruangan else "-",
                "kapasitas": ruangan.kapasitas if ruangan else 0,
            },
        }
        schedule_map[s.id] = item
        detailed_schedules.append(item)

    enriched_conflicts = []
    for c in conflicts:
        affected_details = [
            schedule_map.get(sid, {"id": sid})
            for sid in c.get("affected_schedules", [])
        ]
        enriched_conflicts.append({
            **c,
            "affected_schedule_details": affected_details,
        })

    return {
        "total_jadwal": len(schedules),
        "total_konflik": len(enriched_conflicts),
        "conflicts": enriched_conflicts,
        "schedules": detailed_schedules,
    }


@router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard():
    return """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Conflict Resolver Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 24px; background: #f5f7fb; color: #1e293b; }
        .nav { margin-bottom: 20px; display: flex; gap: 12px; flex-wrap: wrap; }
        .nav a { background: #263B5E; color: #fff; text-decoration: none; padding: 8px 14px; border-radius: 6px; font-size: 14px; }
        .card { background: #fff; border-radius: 8px; padding: 18px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; font-size: 14px; }
        th { background: #263B5E; color: #fff; }
        button { background: #2563eb; color: #fff; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; }
        .badge { padding: 3px 8px; border-radius: 4px; font-size: 12px; background: #fee2e2; color: #991b1b; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/dashboard">Conflict Resolver Jadwal</a>
        <a href="/grades-ui">Form Input Nilai & Riwayat</a>
        <a href="/finance-dashboard">Dashboard Keuangan SPP</a>
        <a href="/attendance-ui">Presensi QR Code (Minggu 12)</a>
        <a href="/docs">Swagger API Docs</a>
    </div>
    <h1>Conflict Resolver Dashboard — Admin Jadwal & Ruangan</h1>
    <div class="card">
        <div id="stats">Loading stats...</div>
        <button onclick="loadDashboard()" style="margin-top:8px;">Refresh Data</button>
    </div>
    <div class="card">
        <h2>Daftar Konflik Jadwal Terdeteksi</h2>
        <table>
            <thead>
                <tr>
                    <th>Jenis Bentrok</th>
                    <th>Deskripsi</th>
                    <th>Jadwal Terdampak</th>
                </tr>
            </thead>
            <tbody id="conflict-list"></tbody>
        </table>
    </div>
    <div class="card">
        <h2>Daftar Jadwal Kuliah, Ruangan & Dosen</h2>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Mata Kuliah</th>
                    <th>Hari & Jam</th>
                    <th>Ruangan (Kapasitas)</th>
                    <th>Dosen</th>
                    <th>Rekomendasi Alternatif (3 Slot)</th>
                </tr>
            </thead>
            <tbody id="schedule-list"></tbody>
        </table>
    </div>
    <div class="card" id="suggestion-box" style="display:none;">
        <h3>Rekomendasi 3 Alternatif Jadwal</h3>
        <pre id="suggestion-output" style="background:#f1f5f9;padding:12px;border-radius:6px;overflow:auto;"></pre>
    </div>
    <script>
        async function loadDashboard() {
            const res = await fetch('/api/admin/scheduling/dashboard');
            const data = await res.json();
            document.getElementById('stats').innerText =
                `Total Jadwal Aktif: ${data.total_jadwal} | Total Konflik Terdeteksi: ${data.total_konflik}`;

            const cBody = document.getElementById('conflict-list');
            cBody.innerHTML = '';
            if (!data.conflicts || data.conflicts.length === 0) {
                cBody.innerHTML = '<tr><td colspan="3">Tidak ada jadwal bentrok saat ini.</td></tr>';
            } else {
                data.conflicts.forEach(c => {
                    cBody.innerHTML += `<tr>
                        <td><span class="badge">${c.type}</span></td>
                        <td>${c.description}</td>
                        <td>Jadwal ID: ${(c.affected_schedules || []).join(', ')}</td>
                    </tr>`;
                });
            }

            const sBody = document.getElementById('schedule-list');
            sBody.innerHTML = '';
            (data.schedules || []).forEach(s => {
                sBody.innerHTML += `<tr>
                    <td>${s.id}</td>
                    <td>${s.matakuliah.kode_mk} - ${s.matakuliah.nama_mk}</td>
                    <td>${s.hari}, ${s.jam_mulai} - ${s.jam_selesai}</td>
                    <td>${s.ruangan.kode_ruangan} - ${s.ruangan.nama_ruangan} (${s.ruangan.kapasitas})</td>
                    <td>${s.dosen.nidn} - ${s.dosen.nama}</td>
                    <td><button onclick="getSuggestions(${s.id})">Cek 3 Alternatif</button></td>
                </tr>`;
            });
        }

        async function getSuggestions(id) {
            const res = await fetch(`/api/schedules/${id}/suggestions`, {method: 'POST'});
            const data = await res.json();
            document.getElementById('suggestion-box').style.display = 'block';
            document.getElementById('suggestion-output').innerText = JSON.stringify(data, null, 2);
        }

        loadDashboard();
    </script>
</body>
</html>"""


@router.get("/grades-ui", response_class=HTMLResponse)
def grades_management_ui():
    return """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Form Input Nilai & Transkrip Akademik</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 24px; background: #f5f7fb; color: #1e293b; }
        .nav { margin-bottom: 20px; display: flex; gap: 12px; flex-wrap: wrap; }
        .nav a { background: #263B5E; color: #fff; text-decoration: none; padding: 8px 14px; border-radius: 6px; font-size: 14px; }
        .card { background: #fff; border-radius: 8px; padding: 18px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
        label { display: block; margin-top: 8px; font-weight: 600; font-size: 14px; }
        input, select { width: 100%; max-width: 360px; padding: 7px; margin-top: 4px; border: 1px solid #cbd5e1; border-radius: 4px; }
        button { background: #2563eb; color: #fff; border: none; padding: 8px 14px; border-radius: 4px; cursor: pointer; margin-top: 12px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #cbd5e1; padding: 8px; text-align: left; font-size: 14px; }
        th { background: #263B5E; color: #fff; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/dashboard">Conflict Resolver Jadwal</a>
        <a href="/grades-ui">Form Input Nilai & Riwayat</a>
        <a href="/finance-dashboard">Dashboard Keuangan SPP</a>
        <a href="/attendance-ui">Presensi QR Code (Minggu 12)</a>
        <a href="/docs">Swagger API Docs</a>
    </div>
    <h1>Form Input Nilai Dosen & Audit Trail Nilai</h1>
    <div class="card">
        <h2>Input Nilai Mahasiswa</h2>
        <form onsubmit="submitGrade(event)">
            <label>NIM Mahasiswa</label>
            <input id="g_nim" required placeholder="Contoh: 2026110001">
            <label>ID Mata Kuliah</label>
            <input id="g_mk" type="number" min="1" required value="1">
            <label>Semester</label>
            <input id="g_sem" type="number" min="1" required value="1">
            <label>Nilai Huruf</label>
            <select id="g_nilai">
                <option value="A">A (4.0)</option>
                <option value="B">B (3.0)</option>
                <option value="C">C (2.0)</option>
                <option value="D">D (1.0)</option>
                <option value="E">E (0.0)</option>
            </select>
            <label>Persentase Presensi (%)</label>
            <input id="g_presensi" type="number" min="0" max="100" step="0.1" required value="90">
            <label>Diinput Oleh (Dosen)</label>
            <input id="g_by" required value="Dosen Pengampu">
            <br><button type="submit">Simpan Nilai</button>
        </form>
        <div id="grade-msg" style="margin-top:10px;font-weight:bold;"></div>
    </div>
    <div class="card">
        <h2>Edit Nilai Mahasiswa (Wajib Alasan Perubahan / Audit Trail)</h2>
        <form onsubmit="updateGrade(event)">
            <label>ID Nilai (Grade ID)</label>
            <input id="u_grade_id" type="number" min="1" required placeholder="Contoh: 1">
            <label>NIM Mahasiswa (untuk refresh tabel riwayat)</label>
            <input id="u_nim" required placeholder="Contoh: 2026110001">
            <label>Nilai Huruf Baru</label>
            <select id="u_nilai">
                <option value="A">A (4.0)</option>
                <option value="B">B (3.0)</option>
                <option value="C">C (2.0)</option>
                <option value="D">D (1.0)</option>
                <option value="E">E (0.0)</option>
            </select>
            <label>Diubah Oleh (Dosen / Admin)</label>
            <input id="u_by" required value="Dosen Pengampu">
            <label>Alasan Perubahan Nilai (Minimal 5 Karakter)</label>
            <input id="u_reason" minlength="5" required placeholder="Contoh: Koreksi hasil ujian susulan">
            <br><button type="submit">Update Nilai & Catat Audit Trail</button>
        </form>
        <div id="update-grade-msg" style="margin-top:10px;font-weight:bold;"></div>
    </div>
    <div class="card">
        <h2>Cek IPK, Transkrip PDF & Audit Trail Perubahan Nilai</h2>
        <input id="q_nim" placeholder="Masukkan NIM Mahasiswa" value="2026110001">
        <button onclick="loadStudentAcademic()">Lihat IPK & Riwayat Audit</button>
        <button onclick="downloadPdf()">Download PDF Transkrip</button>
        <div id="ipk-summary" style="margin-top:12px;"></div>
        <table>
            <thead>
                <tr><th>Grade ID</th><th>Nilai Lama</th><th>Nilai Baru</th><th>Diubah Oleh</th><th>Waktu</th><th>Alasan</th></tr>
            </thead>
            <tbody id="history-body"></tbody>
        </table>
    </div>
    <script>
        async function submitGrade(e) {
            e.preventDefault();
            const msg = document.getElementById('grade-msg');
            msg.innerText = 'Menyimpan...';
            const res = await fetch('/api/grades/input', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    nim: document.getElementById('g_nim').value,
                    matakuliah_id: parseInt(document.getElementById('g_mk').value),
                    semester: parseInt(document.getElementById('g_sem').value),
                    nilai_huruf: document.getElementById('g_nilai').value,
                    presensi_persen: parseFloat(document.getElementById('g_presensi').value),
                    changed_by: document.getElementById('g_by').value
                })
            });
            const data = await res.json();
            msg.innerText = res.ok ? `Berhasil: ${data.message} (Grade ID: ${data.grade_id}, Bobot: ${data.bobot})` : `Gagal: ${JSON.stringify(data.detail)}`;
        }
        async function updateGrade(e) {
            e.preventDefault();
            const msg = document.getElementById('update-grade-msg');
            const gradeId = parseInt(document.getElementById('u_grade_id').value);
            const nim = document.getElementById('u_nim').value;
            msg.innerText = 'Memperbarui nilai...';
            const res = await fetch(`/api/grades/update/${gradeId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    nilai_huruf: document.getElementById('u_nilai').value,
                    changed_by: document.getElementById('u_by').value,
                    reason: document.getElementById('u_reason').value
                })
            });
            const data = await res.json();
            if (res.ok) {
                msg.innerText = `Berhasil: ${data.message} (Nilai Lama: ${data.old_value || data.nilai_huruf} -> Nilai Baru: ${data.new_value || data.nilai_huruf})`;
                document.getElementById('q_nim').value = nim;
                await loadStudentAcademic();
            } else {
                msg.innerText = `Gagal: ${JSON.stringify(data.detail)}`;
            }
        }
        async function loadStudentAcademic() {
            const nim = document.getElementById('q_nim').value;
            const ipkRes = await fetch(`/api/grades/ipk/${nim}`);
            const ipkData = await ipkRes.json();
            document.getElementById('ipk-summary').innerText = ipkRes.ok
                ? `NIM: ${ipkData.nim} | IPK: ${ipkData.ipk} | Total SKS: ${ipkData.total_sks} | SKS Lulus: ${ipkData.total_sks_lulus}`
                : `Error: ${JSON.stringify(ipkData.detail)}`;

            const hRes = await fetch(`/api/grades/history/${nim}`);
            const hData = await hRes.json();
            const body = document.getElementById('history-body');
            body.innerHTML = '';
            if (Array.isArray(hData) && hData.length > 0) {
                hData.forEach(r => {
                    body.innerHTML += `<tr>
                        <td>${r.grade_id}</td>
                        <td>${r.nilai_lama || r.old_value}</td>
                        <td>${r.nilai_baru || r.new_value}</td>
                        <td>${r.changed_by}</td>
                        <td>${r.changed_at}</td>
                        <td>${r.reason}</td>
                    </tr>`;
                });
            } else {
                body.innerHTML = '<tr><td colspan="6">Belum ada riwayat perubahan nilai.</td></tr>';
            }
        }
        function downloadPdf() {
            const nim = document.getElementById('q_nim').value;
            window.open(`/api/grades/transcript/${nim}/pdf`, '_blank');
        }
    </script>
</body>
</html>"""


@router.get("/finance-dashboard", response_class=HTMLResponse)
def finance_dashboard_ui():
    return """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Keuangan SPP & AI Financial Insights</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 24px; background: #f5f7fb; color: #1e293b; }
        .nav { margin-bottom: 20px; display: flex; gap: 12px; flex-wrap: wrap; }
        .nav a { background: #263B5E; color: #fff; text-decoration: none; padding: 8px 14px; border-radius: 6px; font-size: 14px; }
        .card { background: #fff; border-radius: 8px; padding: 18px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; font-size: 14px; }
        th { background: #263B5E; color: #fff; }
        button { background: #2563eb; color: #fff; border: none; padding: 8px 14px; border-radius: 4px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/dashboard">Conflict Resolver Jadwal</a>
        <a href="/grades-ui">Form Input Nilai & Riwayat</a>
        <a href="/finance-dashboard">Dashboard Keuangan SPP</a>
        <a href="/attendance-ui">Presensi QR Code (Minggu 12)</a>
        <a href="/docs">Swagger API Docs</a>
    </div>
    <h1>Dashboard Keuangan SPP & AI Financial Insights</h1>
    <div class="card">
        <button onclick="loadFinanceData()">Refresh Data Real-Time</button>
        <div id="ai-insight" style="margin-top:12px;font-weight:bold;">Loading AI Financial Report...</div>
    </div>
    <div class="card">
        <h2>Collection Rate per Program Studi</h2>
        <table>
            <thead><tr><th>Program Studi</th><th>Total Tagihan</th><th>Total Terbayar</th><th>Mahasiswa Lunas</th><th>Collection Rate (%)</th></tr></thead>
            <tbody id="prodi-body"></tbody>
        </table>
    </div>
    <div class="card">
        <h2>Rekap Pembayaran per Bulan</h2>
        <table>
            <thead><tr><th>Bulan</th><th>Total Pembayaran Masuk</th></tr></thead>
            <tbody id="monthly-body"></tbody>
        </table>
    </div>
    <div class="card">
        <h2>Status Tagihan Mahasiswa & Daftar Menunggak</h2>
        <table>
            <thead><tr><th>NIM</th><th>Nama</th><th>Program Studi</th><th>Total Tagihan</th><th>Sudah Bayar</th><th>Sisa Tagihan</th><th>Status</th></tr></thead>
            <tbody id="mhs-body"></tbody>
        </table>
    </div>
    <script>
        async function loadFinanceData() {
            const [dRes, aiRes] = await Promise.all([
                fetch('/api/billing/dashboard'),
                fetch('/api/billing/ai-report')
            ]);
            const d = await dRes.json();
            const ai = await aiRes.json();

            document.getElementById('ai-insight').innerText =
                `Revenue Bulan Ini (${ai.month}): Rp ${ai.total_revenue_this_month} | Collection Rate: ${ai.collection_rate}% | Rekomendasi: ${ai.rekomendasi}`;

            const pBody = document.getElementById('prodi-body');
            pBody.innerHTML = '';
            (d.collection_rate_per_prodi || []).forEach(r => {
                pBody.innerHTML += `<tr><td>${r.program_studi}</td><td>Rp ${r.total_tagihan}</td><td>Rp ${r.total_pembayaran}</td><td>${r.mahasiswa_lunas}/${r.jumlah_mahasiswa}</td><td>${r.collection_rate}%</td></tr>`;
            });

            const mBody = document.getElementById('monthly-body');
            mBody.innerHTML = '';
            (d.grafik_pembayaran_per_bulan || []).forEach(r => {
                mBody.innerHTML += `<tr><td>${r.bulan}</td><td>Rp ${r.total_pembayaran}</td></tr>`;
            });

            const sBody = document.getElementById('mhs-body');
            sBody.innerHTML = '';
            (d.per_mahasiswa || []).forEach(r => {
                sBody.innerHTML += `<tr><td>${r.nim}</td><td>${r.nama}</td><td>${r.program_studi}</td><td>Rp ${r.total_tagihan}</td><td>Rp ${r.total_pembayaran}</td><td>Rp ${r.sisa_tagihan}</td><td>${r.status_pembayaran}</td></tr>`;
            });
        }
        loadFinanceData();
    </script>
</body>
</html>"""
