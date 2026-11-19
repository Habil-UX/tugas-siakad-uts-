from .schedule_subject import Observer
from .notification_manager import NotificationManager
from app.models import CalonMahasiswa, Dosen

class StudentObserver(Observer):
    def __init__(self, db, nim_list: list):
        self.db = db
        self.nim_list = nim_list

    def update(self, event_type: str, data: dict):
        manager = NotificationManager(self.db)
        for nim in self.nim_list:
            manager.send_notification("MAHASISWA", nim, "email", f"Jadwal {data['nama_mk']} berubah. Silakan cek KRS.")

class LecturerObserver(Observer):
    def __init__(self, db, dosen_id: int):
        self.db = db
        self.dosen_id = dosen_id

    def update(self, event_type: str, data: dict):
        manager = NotificationManager(self.db)
        manager.send_notification("DOSEN", str(self.dosen_id), "sms", f"Jadwal mengajar Anda untuk {data['nama_mk']} telah diubah.")

class AdminObserver(Observer):
    def __init__(self, db):
        self.db = db

    def update(self, event_type: str, data: dict):
        manager = NotificationManager(self.db)
        manager.send_notification("ADMIN", "admin_1", "push", f"Perubahan jadwal pada MK {data['nama_mk']}.")