from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models import NotificationLog


class NotificationChannel(ABC):
    """Port / abstraksi kanal pengiriman notifikasi yang dapat ditukar (Email, SMS, Push)."""

    channel_name: str = "log"

    @abstractmethod
    def send(self, recipient_type: str, recipient_id: str, message: str) -> str:
        pass


class EmailChannel(NotificationChannel):
    channel_name = "email"

    def send(self, recipient_type: str, recipient_id: str, message: str) -> str:
        formatted = f"[EMAIL] To {recipient_type} ({recipient_id}): {message}"
        print(formatted)
        return formatted


class SMSChannel(NotificationChannel):
    channel_name = "sms"

    def send(self, recipient_type: str, recipient_id: str, message: str) -> str:
        formatted = f"[SMS] To {recipient_type} ({recipient_id}): {message}"
        print(formatted)
        return formatted


class PushChannel(NotificationChannel):
    channel_name = "push"

    def send(self, recipient_type: str, recipient_id: str, message: str) -> str:
        formatted = f"[PUSH] To {recipient_type} ({recipient_id}): {message}"
        print(formatted)
        return formatted


CHANNEL_REGISTRY: Dict[str, NotificationChannel] = {
    "email": EmailChannel(),
    "sms": SMSChannel(),
    "push": PushChannel(),
}


@dataclass
class OutboxMessage:
    event_type: str
    recipient_type: str
    recipient_id: str
    channel: str
    message: str
    idempotency_key: str
    status: str = "PENDING"
    created_at: datetime = field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None


class Outbox:
    """
    Outbox buffer yang menyimpan pesan notifikasi beserta idempotency_key
    agar hanya dikirim setelah transaksi database berhasil di-commit.
    """

    def __init__(self):
        self._entries: List[OutboxMessage] = []
        self._seen_keys: set[str] = set()

    def enqueue(
        self,
        event_type: str,
        recipient_type: str,
        recipient_id: str,
        channel: str,
        message: str,
        idempotency_key: Optional[str] = None,
    ) -> Optional[OutboxMessage]:
        key = idempotency_key or f"{event_type}:{recipient_type}:{recipient_id}:{channel}:{message}"
        if key in self._seen_keys:
            return None
        self._seen_keys.add(key)
        entry = OutboxMessage(
            event_type=event_type,
            recipient_type=recipient_type,
            recipient_id=str(recipient_id),
            channel=channel,
            message=message,
            idempotency_key=key,
        )
        self._entries.append(entry)
        return entry

    @property
    def entries(self) -> List[OutboxMessage]:
        return list(self._entries)

    @property
    def pending_entries(self) -> List[OutboxMessage]:
        return [e for e in self._entries if e.status == "PENDING"]


class OutboxDispatcher:
    """
    Mengirim seluruh pesan PENDING dari Outbox setelah transaksi utama di-commit
    (outbox + kirim setelah commit), lengkap dengan isolasi try/except dan idempotency.
    """

    def __init__(self, db: Optional[Session] = None, channels: Optional[Dict[str, NotificationChannel]] = None):
        self.db = db
        self.channels = channels or dict(CHANNEL_REGISTRY)
        self.dispatched_keys: set[str] = set()

    def dispatch_after_commit(self, outbox: Outbox) -> List[OutboxMessage]:
        sent: List[OutboxMessage] = []
        for entry in outbox.pending_entries:
            if entry.idempotency_key in self.dispatched_keys:
                entry.status = "SKIPPED_DUPLICATE"
                continue

            channel_adapter = self.channels.get(entry.channel.lower(), EmailChannel())
            try:
                channel_adapter.send(entry.recipient_type, entry.recipient_id, entry.message)
                entry.status = "SENT"
                entry.sent_at = datetime.utcnow()
                self.dispatched_keys.add(entry.idempotency_key)
                if self.db is not None and isinstance(self.db, Session):
                    log = NotificationLog(
                        event_type=entry.event_type,
                        recipient_type=entry.recipient_type,
                        recipient_id=entry.recipient_id,
                        channel=entry.channel,
                        message=entry.message,
                        status="SENT",
                    )
                    self.db.add(log)
                    self.db.commit()
                sent.append(entry)
            except Exception as exc:
                entry.status = f"FAILED: {exc}"
        return sent
