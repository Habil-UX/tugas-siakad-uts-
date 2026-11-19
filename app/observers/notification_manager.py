from sqlalchemy.orm import Session
from app.models import NotificationLog

class NotificationManager:
    def __init__(self, db: Session):
        self.db = db

    def send_notification(self, recipient_type: str, recipient_id: str, channel: str, message: str):
        # Simulasi pengiriman (Log ke console)
        print(f"[{channel.upper()}] To {recipient_type} ({recipient_id}): {message}")
        
        # Simpan ke Database
        log = NotificationLog(
            event_type="SCHEDULE_CHANGE",
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            channel=channel,
            message=message,
            status="SENT"
        )
        self.db.add(log)
        self.db.commit()