from datetime import date
import os
import threading
from typing import Dict, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.billing_service import BillingService


class BillingScheduler:
    """
    Pengelola scheduled job untuk modul Keuangan SPP menggunakan APScheduler
    (BackgroundScheduler + CronTrigger):
    - Job 1 (semester_billing_generator): Generate tagihan SPP tiap awal semester
      (1 Februari dan 1 Agustus pukul 00:00).
    - Job 2 (overdue_billing_reminder): Kirim reminder otomatis setiap hari pukul 08:00
      untuk mahasiswa yang memiliki tagihan SPP overdue.
    Dilengkapi lock & guard agar tidak berjalan ganda saat uvicorn --reload.
    """

    _lock = threading.Lock()

    def __init__(self):
        self.scheduler: BackgroundScheduler = BackgroundScheduler()
        self.jobs: Dict[str, dict] = {}
        self.is_running: bool = False
        self._register_default_jobs()

    def _register_default_jobs(self):
        semester_trigger = CronTrigger.from_crontab("0 0 1 2,8 *")
        reminder_trigger = CronTrigger.from_crontab("0 8 * * *")

        self.scheduler.add_job(
            self._scheduled_semester_billing_task,
            trigger=semester_trigger,
            id="semester_billing_generator",
            name="Generate tagihan SPP tiap awal semester",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.add_job(
            self._scheduled_overdue_reminder_task,
            trigger=reminder_trigger,
            id="overdue_billing_reminder",
            name="Kirim reminder otomatis tagihan SPP overdue",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

        self.jobs["semester_billing_generator"] = {
            "id": "semester_billing_generator",
            "description": "Generate tagihan SPP tiap awal semester untuk seluruh mahasiswa aktif",
            "cron": "0 0 1 2,8 *",
        }
        self.jobs["overdue_billing_reminder"] = {
            "id": "overdue_billing_reminder",
            "description": "Kirim reminder otomatis untuk mahasiswa dengan tagihan SPP overdue",
            "cron": "0 8 * * *",
        }

    def _scheduled_semester_billing_task(self):
        db = SessionLocal()
        try:
            today = date.today()
            semester = 1 if today.month >= 8 else 2
            tahun = (
                f"{today.year}/{today.year + 1}"
                if semester == 1
                else f"{today.year - 1}/{today.year}"
            )
            self.run_semester_billing_job(
                db=db,
                semester=semester,
                tahun=tahun,
                semester_start_date=today,
            )
        finally:
            db.close()

    def _scheduled_overdue_reminder_task(self):
        db = SessionLocal()
        try:
            self.run_overdue_reminder_job(db=db, as_of_date=date.today())
        finally:
            db.close()

    def start(self):
        with self._lock:
            # Cegah duplikasi pada proses watcher parent saat uvicorn --reload
            if os.environ.get("UVICORN_RELOAD_WATCHER") == "1":  # pragma: no cover
                return {"status": "skipped_watcher", "jobs": list(self.jobs.values())}

            if not self.scheduler.running:
                self.scheduler.start()
            self.is_running = True
            return self.get_status()

    def shutdown(self):
        with self._lock:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
            self.is_running = False
            self.scheduler = BackgroundScheduler()
            self._register_default_jobs()
            return {"status": "stopped"}

    def get_status(self) -> dict:
        apscheduler_jobs = []
        for job in self.scheduler.get_jobs():
            next_run = getattr(job, "next_run_time", None)
            apscheduler_jobs.append({
                "id": job.id,
                "name": job.name,
                "trigger": str(job.trigger),
                "next_run_time": str(next_run) if next_run else None,
            })
        return {
            "status": "running" if self.scheduler.running else "stopped",
            "is_running": bool(self.scheduler.running),
            "scheduler_class": self.scheduler.__class__.__name__,
            "jobs": apscheduler_jobs,
        }

    def run_semester_billing_job(
        self,
        db: Session,
        semester: int = 1,
        tahun: str = "2026/2027",
        semester_start_date: Optional[date] = None,
    ) -> dict:
        service = BillingService(db)
        return service.generate_semester_billing(
            semester=semester,
            tahun=tahun,
            semester_start_date=semester_start_date or date.today(),
        )

    def run_overdue_reminder_job(
        self,
        db: Session,
        as_of_date: Optional[date] = None,
    ) -> dict:
        service = BillingService(db)
        return service.send_overdue_reminders(as_of_date=as_of_date)


billing_scheduler = BillingScheduler()
