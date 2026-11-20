from typing import Optional
from .schedule_subject import Observer
from .notification_manager import NotificationManager
from .outbox import Outbox, NotificationChannel, EmailChannel, SMSChannel, PushChannel


class StudentObserver(Observer):
    def __init__(
        self,
        db,
        nim_list: list,
        channel: Optional[str | NotificationChannel] = None,
        outbox: Optional[Outbox] = None,
    ):
        self.db = db
        self.nim_list = nim_list
        self.channel_obj = channel if isinstance(channel, NotificationChannel) else EmailChannel()
        self.channel = channel.channel_name if isinstance(channel, NotificationChannel) else (channel or "email")
        self.outbox = outbox

    def update(self, event_type: str, data: dict):
        msg = f"Jadwal {data['nama_mk']} berubah. Silakan cek KRS."
        schedule_id = data.get("id", "0")
        if self.outbox is not None:
            for nim in self.nim_list:
                self.outbox.enqueue(
                    event_type=event_type,
                    recipient_type="MAHASISWA",
                    recipient_id=str(nim),
                    channel=self.channel,
                    message=msg,
                    idempotency_key=f"{event_type}:{schedule_id}:MAHASISWA:{nim}",
                )
            return

        manager = NotificationManager(self.db)
        for nim in self.nim_list:
            manager.send_notification("MAHASISWA", nim, self.channel, msg)


class LecturerObserver(Observer):
    def __init__(
        self,
        db,
        dosen_id: int,
        channel: Optional[str | NotificationChannel] = None,
        outbox: Optional[Outbox] = None,
    ):
        self.db = db
        self.dosen_id = dosen_id
        self.channel_obj = channel if isinstance(channel, NotificationChannel) else SMSChannel()
        self.channel = channel.channel_name if isinstance(channel, NotificationChannel) else (channel or "sms")
        self.outbox = outbox

    def update(self, event_type: str, data: dict):
        msg = f"Jadwal mengajar Anda untuk {data['nama_mk']} telah diubah."
        schedule_id = data.get("id", "0")
        if self.outbox is not None:
            self.outbox.enqueue(
                event_type=event_type,
                recipient_type="DOSEN",
                recipient_id=str(self.dosen_id),
                channel=self.channel,
                message=msg,
                idempotency_key=f"{event_type}:{schedule_id}:DOSEN:{self.dosen_id}",
            )
            return

        manager = NotificationManager(self.db)
        manager.send_notification("DOSEN", str(self.dosen_id), self.channel, msg)


class AdminObserver(Observer):
    def __init__(
        self,
        db,
        channel: Optional[str | NotificationChannel] = None,
        outbox: Optional[Outbox] = None,
    ):
        self.db = db
        self.channel_obj = channel if isinstance(channel, NotificationChannel) else PushChannel()
        self.channel = channel.channel_name if isinstance(channel, NotificationChannel) else (channel or "push")
        self.outbox = outbox

    def update(self, event_type: str, data: dict):
        msg = f"Perubahan jadwal pada MK {data['nama_mk']}."
        schedule_id = data.get("id", "0")
        if self.outbox is not None:
            self.outbox.enqueue(
                event_type=event_type,
                recipient_type="ADMIN",
                recipient_id="admin_1",
                channel=self.channel,
                message=msg,
                idempotency_key=f"{event_type}:{schedule_id}:ADMIN:admin_1",
            )
            return

        manager = NotificationManager(self.db)
        manager.send_notification("ADMIN", "admin_1", self.channel, msg)
