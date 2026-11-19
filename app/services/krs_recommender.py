from sqlalchemy.orm import Session
from app.models import Matakuliah, CalonMahasiswa, RiwayatNilai, SkalaNilai, Prerequisite
from app.schemas.krs import RecommendationResponse, MKRecommendation

class KRSRecommender:
    def __init__(self, db: Session):
        self.db = db
        self.max_sks = 24
        self.best_score = -1
        self.best_selection = []
        self.best_sks = 0

    def _check_prerequisite(self, nim: str, mk_id: int) -> bool:
        """Cek apakah mahasiswa sudah lulus prasyarat (>= C)"""
        bobot_c = self.db.query(SkalaNilai.bobot).filter(SkalaNilai.nilai_huruf == 'C').scalar() or 2.0
        
        prereqs = self.db.query(Prerequisite).filter(Prerequisite.matakuliah_id == mk_id).all()
        for p in prereqs:
            # Cek riwayat nilai
            passed = self.db.query(RiwayatNilai).join(SkalaNilai).filter(
                RiwayatNilai.nim == nim,
                RiwayatNilai.matakuliah_id == p.prerequisite_id,
                SkalaNilai.bobot >= bobot_c
            ).first()
            if not passed:
                return False
        return True

    def _is_conflict(self, mk1: Matakuliah, mk2: Matakuliah) -> bool:
        """Cek bentrok jadwal"""
        if mk1.hari != mk2.hari:
            return False
        # Interval setengah terbuka [start, end)
        return mk1.jam_mulai < mk2.jam_selesai and mk2.jam_mulai < mk1.jam_selesai

    def _backtrack(self, courses: list, index: int, current_sks: int, current_schedule: list, current_selection: list):
        # Hitung skor: Prioritaskan jumlah MK Wajib (bobot 1000), lalu total SKS
        wajib_count = sum(1 for c in current_selection if c.jenis_mk == 'Wajib')
        score = (wajib_count * 1000) + current_sks
        
        if score > self.best_score:
            self.best_score = score
            self.best_selection = list(current_selection)
            self.best_sks = current_sks

        if index >= len(courses):
            return

        for i in range(index, len(courses)):
            course = courses[i]
            
            # Constraint 1: Max SKS
            if current_sks + course.sks > self.max_sks:
                continue
                
            # Constraint 2: Bentrok Jadwal
            has_conflict = any(self._is_conflict(course, existing) for existing in current_schedule)
            if has_conflict:
                continue

            # Ambil MK
            current_selection.append(course)
            current_schedule.append(course)
            
            # Rekursi
            self._backtrack(courses, i + 1, current_sks + course.sks, current_schedule, current_selection)
            
            # Backtrack (Batalkan pilihan)
            current_selection.pop()
            current_schedule.pop()

    def generate_recommendation(self, nim: str) -> RecommendationResponse:
        # 1. Validasi Mahasiswa
        mhs = self.db.query(CalonMahasiswa).filter(CalonMahasiswa.nim == nim).first()
        if not mhs:
            raise ValueError("Mahasiswa tidak ditemukan")

        # 2. Ambil semua MK yang prasyaratnya terpenuhi
        all_mk = self.db.query(Matakuliah).all()
        valid_mk = []
        alasan_tidak_terpilih = {}
        
        for mk in all_mk:
            if self._check_prerequisite(nim, mk.id):
                valid_mk.append(mk)
            else:
                alasan_tidak_terpilih[mk.kode_mk] = "Prasyarat belum terpenuhi"

        # 3. Urutkan: Wajib dulu, lalu SKS terbesar (untuk optimasi packing)
        # Ini membantu algoritma menemukan kombinasi terbaik lebih cepat
        valid_mk.sort(key=lambda x: (0 if x.jenis_mk == 'Wajib' else 1, -x.sks))

        # 4. Jalankan Backtracking
        self.best_score = -1
        self.best_selection = []
        self.best_sks = 0
        self._backtrack(valid_mk, 0, 0, [], [])

        # 5. Susun Output
        selected_codes = [mk.kode_mk for mk in self.best_selection]
        wajib_codes = [mk.kode_mk for mk in self.best_selection if mk.jenis_mk == 'Wajib']
        pilihan_codes = [mk.kode_mk for mk in self.best_selection if mk.jenis_mk == 'Pilihan']

        # Cari alasan untuk MK yang valid tapi tidak terpilih
        for mk in valid_mk:
            if mk.kode_mk not in selected_codes:
                # Cek apakah karena bentrok atau SKS penuh
                conflict = False
                for sel in self.best_selection:
                    if self._is_conflict(mk, sel):
                        conflict = True
                        alasan_tidak_terpilih[mk.kode_mk] = f"Bentrok jadwal dengan {sel.nama_mk}"
                        break
                if not conflict:
                    alasan_tidak_terpilih[mk.kode_mk] = f"Melebihi kuota SKS (Total KRS saat ini: {self.best_sks})"

        return RecommendationResponse(
            nim=nim,
            total_sks=self.best_sks,
            rekomendasi_mk=[
                MKRecommendation(
                    kode_mk=mk.kode_mk,
                    nama_mk=mk.nama_mk,
                    jenis_mk=mk.jenis_mk,
                    sks=mk.sks,
                    hari=mk.hari,
                    jam_mulai=mk.jam_mulai.strftime("%H:%M"),
                    jam_selesai=mk.jam_selesai.strftime("%H:%M")
                ) for mk in self.best_selection
            ],
            wajib_terpilih=wajib_codes,
            pilihan_terpilih=pilihan_codes,
            alasan_tidak_terpilih=alasan_tidak_terpilih
        )