from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    Billing,
    CalonMahasiswa,
    NotificationLog,
    Payment,
    ProgramStudi,
    StatusPendaftaran,
)


class BillingService:

    TARIFFS = {
        "teknik": Decimal("5000000.00"),
        "ekonomi": Decimal("4000000.00"),
    }

    LATE_FEE_RATE = Decimal("0.01")
    LATE_FEE_PERIOD_DAYS = 30
    BILLING_DUE_DAYS = 14

    def __init__(self, db: Session):
        self.db = db

    def _get_mahasiswa(self, nim: str):
        mahasiswa = (
            self.db.query(CalonMahasiswa)
            .filter(CalonMahasiswa.nim == nim)
            .first()
        )

        if not mahasiswa:
            raise HTTPException(
                status_code=404,
                detail="Mahasiswa tidak ditemukan",
            )

        return mahasiswa

    def _get_tariff(self, mahasiswa):
        program = mahasiswa.program_studi

        if not program:
            raise HTTPException(
                status_code=400,
                detail="Program studi mahasiswa tidak ditemukan",
            )

        explicit_tarif = getattr(program, "tarif_spp", None)
        if explicit_tarif is not None and Decimal(str(explicit_tarif)) > 0:
            return Decimal(str(explicit_tarif)).quantize(Decimal("0.01"))

        program_info = (
            f"{program.nama} {program.fakultas}"
        ).lower()

        if "ekonomi" in program_info:
            return self.TARIFFS["ekonomi"]

        if "teknik" in program_info:
            return self.TARIFFS["teknik"]

        raise HTTPException(
            status_code=400,
            detail="Tarif program studi belum dikonfigurasi",
        )

    def _get_billing(self, billing_id: int):
        billing = (
            self.db.query(Billing)
            .filter(Billing.id == billing_id)
            .first()
        )

        if not billing:
            raise HTTPException(
                status_code=404,
                detail="Tagihan tidak ditemukan",
            )

        return billing

    def _get_paid_amount(self, billing_id: int):
        total = (
            self.db.query(
                func.coalesce(
                    func.sum(Payment.amount),
                    0,
                )
            )
            .filter(
                Payment.billing_id == billing_id,
                Payment.status == "success",
            )
            .scalar()
        )

        return Decimal(str(total or 0))

    def generate_billing(
        self,
        nim: str,
        semester: int,
        tahun: str,
        semester_start_date: date,
    ):
        if semester < 1:
            raise HTTPException(
                status_code=400,
                detail="Semester minimal 1",
            )

        mahasiswa = self._get_mahasiswa(nim)

        existing = (
            self.db.query(Billing)
            .filter(
                Billing.nim == nim,
                Billing.semester_akademik == semester,
                Billing.tahun_akademik == tahun,
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Tagihan semester ini sudah tersedia",
            )

        amount = self._get_tariff(mahasiswa)

        due_date = (
            semester_start_date
            + timedelta(days=self.BILLING_DUE_DAYS)
        )

        billing = Billing(
            nim=nim,
            semester_akademik=semester,
            tahun_akademik=tahun,
            amount=amount,
            due_date=due_date,
            status="unpaid",
        )

        try:
            self.db.add(billing)
            self.db.commit()
            self.db.refresh(billing)

            return {
                "message": "Tagihan SPP berhasil dibuat",
                "billing_id": billing.id,
                "nim": billing.nim,
                "semester": billing.semester_akademik,
                "tahun_akademik": billing.tahun_akademik,
                "amount": str(billing.amount),
                "due_date": str(billing.due_date),
                "status": billing.status,
            }

        except Exception:
            self.db.rollback()
            raise

    def generate_semester_billing(
        self,
        semester: int,
        tahun: str,
        semester_start_date: Optional[date] = None,
    ):
        """
        Generate tagihan SPP setiap semester untuk seluruh mahasiswa aktif (approved).
        Bersifat idempotent: tidak menghasilkan tagihan ganda ketika dijalankan berulang.
        """
        if semester < 1:
            raise HTTPException(
                status_code=400,
                detail="Semester minimal 1",
            )

        if semester_start_date is None:
            semester_start_date = date.today()

        due_date = semester_start_date + timedelta(days=self.BILLING_DUE_DAYS)

        active_students = (
            self.db.query(CalonMahasiswa)
            .filter(
                CalonMahasiswa.status == StatusPendaftaran.approved,
                CalonMahasiswa.nim.isnot(None),
            )
            .all()
        )

        created = []
        skipped = []

        try:
            for mhs in active_students:
                existing = (
                    self.db.query(Billing)
                    .filter(
                        Billing.nim == mhs.nim,
                        Billing.semester_akademik == semester,
                        Billing.tahun_akademik == tahun,
                    )
                    .first()
                )
                if existing:
                    skipped.append(mhs.nim)
                    continue

                amount = self._get_tariff(mhs)
                billing = Billing(
                    nim=mhs.nim,
                    semester_akademik=semester,
                    tahun_akademik=tahun,
                    amount=amount,
                    due_date=due_date,
                    status="unpaid",
                )
                self.db.add(billing)
                self.db.flush()
                created.append({
                    "billing_id": billing.id,
                    "nim": billing.nim,
                    "amount": str(billing.amount),
                    "due_date": str(billing.due_date),
                    "status": billing.status,
                })

            self.db.commit()
            return {
                "message": "Proses generate tagihan semester selesai",
                "semester": semester,
                "tahun_akademik": tahun,
                "created_count": len(created),
                "skipped_count": len(skipped),
                "created_billings": created,
                "skipped_nims": skipped,
            }
        except Exception:
            self.db.rollback()
            raise

    def calculate_late_fee(
        self,
        billing_id: int,
        as_of_date: date = None,
    ):
        billing = self._get_billing(billing_id)

        if as_of_date is None:
            as_of_date = date.today()

        paid_amount = self._get_paid_amount(billing_id)

        outstanding = max(
            Decimal("0.00"),
            Decimal(str(billing.amount)) - paid_amount,
        )

        overdue_days = max(
            0,
            (as_of_date - billing.due_date).days,
        )

        months_late = (
            overdue_days // self.LATE_FEE_PERIOD_DAYS
        )

        late_fee = (
            outstanding
            * self.LATE_FEE_RATE
            * Decimal(months_late)
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        return {
            "billing_id": billing.id,
            "amount": str(billing.amount),
            "paid_amount": str(paid_amount),
            "outstanding": str(outstanding),
            "overdue_days": overdue_days,
            "months_late": months_late,
            "late_fee": str(late_fee),
            "total_due": str(outstanding + late_fee),
        }

    def update_billing_status(
        self,
        billing_id: int,
        as_of_date: date = None,
    ):
        billing = self._get_billing(billing_id)

        if as_of_date is None:
            as_of_date = date.today()

        paid_amount = self._get_paid_amount(billing_id)
        amount = Decimal(str(billing.amount))

        if paid_amount >= amount:
            status = "paid"
        elif as_of_date > billing.due_date:
            status = "overdue"
        elif paid_amount > 0:
            status = "partial"
        else:
            status = "unpaid"

        try:
            billing.status = status
            self.db.commit()
            self.db.refresh(billing)

            return {
                "billing_id": billing.id,
                "nim": billing.nim,
                "status": billing.status,
                "paid_amount": str(paid_amount),
                "remaining_amount": str(
                    max(
                        Decimal("0.00"),
                        amount - paid_amount,
                    )
                ),
            }

        except Exception:
            self.db.rollback()
            raise

    def send_overdue_reminders(self, as_of_date: Optional[date] = None) -> dict:
        if as_of_date is None:
            as_of_date = date.today()

        billings = self.db.query(Billing).all()
        reminded = []

        for b in billings:
            paid = self._get_paid_amount(b.id)
            amount = Decimal(str(b.amount))
            remaining = max(Decimal("0.00"), amount - paid)
            if remaining > 0 and as_of_date > b.due_date:
                b.status = "overdue"
                overdue_days = (as_of_date - b.due_date).days
                msg = (
                    f"Reminder SPP: Tagihan semester {b.semester_akademik} ({b.tahun_akademik}) "
                    f"sebesar Rp{remaining} telah melewati jatuh tempo ({overdue_days} hari)."
                )
                self.db.add(
                    NotificationLog(
                        event_type="BILLING_REMINDER",
                        recipient_type="MAHASISWA",
                        recipient_id=b.nim,
                        channel="email",
                        message=msg,
                        status="SENT",
                    )
                )
                reminded.append({
                    "billing_id": b.id,
                    "nim": b.nim,
                    "remaining_amount": str(remaining),
                    "overdue_days": overdue_days,
                })

        self.db.commit()
        return {
            "as_of_date": str(as_of_date),
            "reminders_sent": len(reminded),
            "details": reminded,
        }

    def get_financial_dashboard_data(self, as_of_date: Optional[date] = None) -> dict:
        if as_of_date is None:
            as_of_date = date.today()

        billings = self.db.query(Billing).all()
        student_map = {}

        for b in billings:
            paid = self._get_paid_amount(b.id)
            total = Decimal(str(b.amount))
            sisa = max(Decimal("0.00"), total - paid)

            if paid >= total:
                eff_status = "paid"
            elif as_of_date > b.due_date:
                eff_status = "overdue"
            elif paid > 0:
                eff_status = "partial"
            else:
                eff_status = "unpaid"

            mhs = b.mahasiswa
            prodi_nama = (
                mhs.program_studi.nama
                if mhs and mhs.program_studi
                else "Tidak Diketahui"
            )
            nama_mhs = mhs.nama_lengkap if mhs else b.nim

            entry = student_map.setdefault(
                b.nim,
                {
                    "nim": b.nim,
                    "nama": nama_mhs,
                    "program_studi": prodi_nama,
                    "total_tagihan": Decimal("0.00"),
                    "total_pembayaran": Decimal("0.00"),
                    "sisa_tagihan": Decimal("0.00"),
                    "statuses": [],
                    "max_overdue_days": 0,
                },
            )
            entry["total_tagihan"] += total
            entry["total_pembayaran"] += paid
            entry["sisa_tagihan"] += sisa
            entry["statuses"].append(eff_status)
            if sisa > 0 and as_of_date > b.due_date:
                entry["max_overdue_days"] = max(
                    entry["max_overdue_days"],
                    (as_of_date - b.due_date).days,
                )

        per_mahasiswa = []
        daftar_menunggak = []

        for nim, info in student_map.items():
            statuses = info["statuses"]
            if all(s == "paid" for s in statuses):
                overall = "paid"
            elif "overdue" in statuses:
                overall = "overdue"
            elif "partial" in statuses or info["total_pembayaran"] > 0:
                overall = "partial"
            else:
                overall = "unpaid"

            row = {
                "nim": nim,
                "nama": info["nama"],
                "program_studi": info["program_studi"],
                "total_tagihan": str(info["total_tagihan"].quantize(Decimal("0.01"))),
                "total_pembayaran": str(info["total_pembayaran"].quantize(Decimal("0.01"))),
                "sisa_tagihan": str(info["sisa_tagihan"].quantize(Decimal("0.01"))),
                "status_pembayaran": overall,
            }
            per_mahasiswa.append(row)

            if info["sisa_tagihan"] > 0:
                daftar_menunggak.append({
                    **row,
                    "overdue_days": info["max_overdue_days"],
                    "months_late": info["max_overdue_days"] // self.LATE_FEE_PERIOD_DAYS,
                })

        # Collection rate per program studi
        prodi_stats = {}
        for row in per_mahasiswa:
            p_name = row["program_studi"]
            ps = prodi_stats.setdefault(
                p_name,
                {
                    "program_studi": p_name,
                    "total_tagihan": Decimal("0.00"),
                    "total_pembayaran": Decimal("0.00"),
                    "jumlah_mahasiswa": 0,
                    "mahasiswa_lunas": 0,
                },
            )
            ps["total_tagihan"] += Decimal(row["total_tagihan"])
            ps["total_pembayaran"] += Decimal(row["total_pembayaran"])
            ps["jumlah_mahasiswa"] += 1
            if row["status_pembayaran"] == "paid":
                ps["mahasiswa_lunas"] += 1

        collection_rate_per_prodi = []
        for p_name, ps in prodi_stats.items():
            rate = (
                round(
                    float(ps["total_pembayaran"] / ps["total_tagihan"] * 100),
                    2,
                )
                if ps["total_tagihan"] > 0
                else 0.0
            )
            collection_rate_per_prodi.append({
                "program_studi": p_name,
                "total_tagihan": str(ps["total_tagihan"].quantize(Decimal("0.01"))),
                "total_pembayaran": str(ps["total_pembayaran"].quantize(Decimal("0.01"))),
                "jumlah_mahasiswa": ps["jumlah_mahasiswa"],
                "mahasiswa_lunas": ps["mahasiswa_lunas"],
                "collection_rate": rate,
            })

        # Grafik pembayaran per bulan
        payments = (
            self.db.query(Payment)
            .filter(Payment.status == "success")
            .all()
        )
        monthly_map = {}
        for p in payments:
            dt = p.paid_at or p.created_at
            month_key = dt.strftime("%Y-%m") if dt else "Unknown"
            monthly_map[month_key] = monthly_map.get(month_key, Decimal("0.00")) + Decimal(str(p.amount))

        grafik_pembayaran_per_bulan = [
            {
                "bulan": k,
                "total_pembayaran": str(v.quantize(Decimal("0.01"))),
            }
            for k, v in sorted(monthly_map.items())
        ]

        return {
            "per_mahasiswa": per_mahasiswa,
            "collection_rate_per_prodi": collection_rate_per_prodi,
            "grafik_pembayaran_per_bulan": grafik_pembayaran_per_bulan,
            "daftar_mahasiswa_menunggak": daftar_menunggak,
        }

    def generate_ai_financial_report(self, as_of_date: Optional[date] = None) -> dict:
        if as_of_date is None:
            as_of_date = date.today()

        dashboard = self.get_financial_dashboard_data(as_of_date=as_of_date)

        # Total revenue bulan ini
        current_month_key = as_of_date.strftime("%Y-%m")
        revenue_this_month = Decimal("0.00")
        for m in dashboard["grafik_pembayaran_per_bulan"]:
            if m["bulan"] == current_month_key:
                revenue_this_month += Decimal(m["total_pembayaran"])

        per_mhs = dashboard["per_mahasiswa"]
        total_mhs = len(per_mhs)
        lunas_mhs = sum(1 for m in per_mhs if m["status_pembayaran"] == "paid")
        collection_rate_pct = (
            round((lunas_mhs / total_mhs) * 100, 2)
            if total_mhs > 0
            else 0.0
        )

        # Top 10 mahasiswa dengan tunggakan terbesar
        arrears = sorted(
            dashboard["daftar_mahasiswa_menunggak"],
            key=lambda x: Decimal(x["sisa_tagihan"]),
            reverse=True,
        )[:10]

        overdue_2m = [
            x
            for x in dashboard["daftar_mahasiswa_menunggak"]
            if x["overdue_days"] > 60 or x["months_late"] >= 2
        ]
        z_count = len(overdue_2m)

        if total_mhs == 0:
            rekomendasi_str = "Belum ada data tagihan atau pembayaran pada sistem."
        else:
            rekomendasi_str = (
                f"Kirim reminder ke {z_count} mahasiswa dengan tunggakan >2 bulan"
            )

        return {
            "as_of_date": str(as_of_date),
            "month": current_month_key,
            "total_revenue_this_month": str(revenue_this_month.quantize(Decimal("0.01"))),
            "collection_rate": collection_rate_pct,
            "total_mahasiswa_tertagih": total_mhs,
            "total_mahasiswa_lunas": lunas_mhs,
            "top_10_mahasiswa_tunggakan_terbesar": arrears,
            "mahasiswa_tunggakan_lebih_2_bulan": overdue_2m,
            "rekomendasi": rekomendasi_str,
        }
