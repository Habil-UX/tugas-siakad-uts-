from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import json
from typing import Optional, Union

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Billing, NotificationLog, Payment, PaymentMethod
from app.utils.security import verify_webhook_signature


class PaymentService:

    CENT = Decimal("0.01")

    def __init__(self, db: Session):
        self.db = db

    def _normalize_amount(self, amount):
        try:
            value = Decimal(str(amount))

            if not value.is_finite():
                raise InvalidOperation

            normalized = value.quantize(self.CENT)

        except (InvalidOperation, TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail="Nominal pembayaran tidak valid",
            )

        if normalized <= 0:
            raise HTTPException(
                status_code=400,
                detail="Nominal pembayaran harus lebih dari 0",
            )

        if normalized != value:
            raise HTTPException(
                status_code=400,
                detail="Nominal pembayaran maksimal 2 angka desimal",
            )

        return normalized

    def _get_billing(self, billing_id: int):
        billing = (
            self.db.query(Billing)
            .filter(Billing.id == billing_id)
            .with_for_update()
            .first()
        )

        if not billing:
            raise HTTPException(
                status_code=404,
                detail="Tagihan tidak ditemukan",
            )

        return billing

    def _get_payment_method(self, method_id: Union[int, str]):
        if isinstance(method_id, int) or (
            isinstance(method_id, str) and method_id.isdigit()
        ):
            method = (
                self.db.query(PaymentMethod)
                .filter(PaymentMethod.id == int(method_id))
                .first()
            )
        else:
            code_str = str(method_id).strip()
            method = (
                self.db.query(PaymentMethod)
                .filter(
                    (PaymentMethod.code == code_str.upper())
                    | (PaymentMethod.name == code_str)
                )
                .first()
            )
            if not method and isinstance(self.db, Session) and code_str:
                method = PaymentMethod(
                    code=code_str.upper()[:30],
                    name=code_str[:100],
                    is_active=True,
                )
                self.db.add(method)
                self.db.flush()

        if not method:
            raise HTTPException(
                status_code=404,
                detail="Metode pembayaran tidak ditemukan",
            )

        if not method.is_active:
            raise HTTPException(
                status_code=400,
                detail="Metode pembayaran tidak aktif",
            )

        return method

    def _get_payment(self, payment_id: int):
        payment = (
            self.db.query(Payment)
            .filter(Payment.id == payment_id)
            .with_for_update()
            .first()
        )

        if not payment:
            raise HTTPException(
                status_code=404,
                detail="Transaksi pembayaran tidak ditemukan",
            )

        return payment

    def _get_total_amount(
        self,
        billing_id: int,
        statuses: list,
    ):
        total = (
            self.db.query(
                func.coalesce(
                    func.sum(Payment.amount),
                    0,
                )
            )
            .filter(
                Payment.billing_id == billing_id,
                Payment.status.in_(statuses),
            )
            .scalar()
        )

        return Decimal(str(total or 0))

    def _sync_billing_status(
        self,
        billing: Billing,
        paid_amount: Decimal,
        as_of_date: date = None,
    ):
        if as_of_date is None:
            as_of_date = date.today()

        amount = Decimal(str(billing.amount))

        if paid_amount >= amount:
            billing.status = "paid"
        elif as_of_date > billing.due_date:
            billing.status = "overdue"
        elif paid_amount > 0:
            billing.status = "partial"
        else:
            billing.status = "unpaid"

    def _send_receipt_email_simulation(
        self,
        nim: str,
        billing_id: int,
        amount: Decimal,
        reference_number: Optional[str],
        billing_status: str,
    ):
        if not isinstance(self.db, Session):
            return
        msg = (
            f"Receipt Pembayaran SPP: Tagihan #{billing_id} sebesar Rp{amount} "
            f"(Ref: {reference_number or '-'}) berhasil diterima. Status tagihan: {billing_status}."
        )
        self.db.add(
            NotificationLog(
                event_type="PAYMENT_RECEIPT",
                recipient_type="MAHASISWA",
                recipient_id=str(nim),
                channel="email",
                message=msg,
                status="SENT",
            )
        )

    def process_payment(
        self,
        billing_id: int,
        amount,
        method: Union[int, str],
        reference_number: Optional[str] = None,
        paid_at: Optional[datetime] = None,
        as_of_date: Optional[date] = None,
    ):
        """
        Memproses pembayaran langsung terhadap tagihan dalam satu transaksi database atomic.
        - Jika total pembayaran < tagihan -> status 'partial' (atau 'overdue' jika lewat jatuh tempo)
        - Jika total pembayaran >= tagihan -> status 'paid'
        - Mencegah pembayaran ganda (idempotent berdasarkan reference_number).
        """
        payment_amount = self._normalize_amount(amount)

        if reference_number is not None:
            ref_clean = str(reference_number).strip()
            if not ref_clean or len(ref_clean) > 100:
                raise HTTPException(
                    status_code=400,
                    detail="Nomor referensi wajib diisi dan maksimal 100 karakter",
                )
            existing_ref = (
                self.db.query(Payment)
                .filter(Payment.reference_number == ref_clean)
                .first()
            )
            if existing_ref:
                if (
                    existing_ref.billing_id == billing_id
                    and Decimal(str(existing_ref.amount)) == payment_amount
                    and existing_ref.status == "success"
                ):
                    billing = self._get_billing(billing_id)
                    return {
                        "message": "Pembayaran sudah diproses sebelumnya",
                        "payment_id": existing_ref.id,
                        "billing_id": billing.id,
                        "reference_number": existing_ref.reference_number,
                        "amount": str(existing_ref.amount),
                        "payment_status": existing_ref.status,
                        "billing_status": billing.status,
                        "idempotent": True,
                    }
                raise HTTPException(
                    status_code=409,
                    detail="Nomor referensi pembayaran sudah digunakan",
                )
        else:
            ref_clean = None

        billing = self._get_billing(billing_id)
        payment_method = self._get_payment_method(method)

        paid_amount = self._get_total_amount(billing.id, ["success"])
        total_tagihan = Decimal(str(billing.amount))
        remaining = total_tagihan - paid_amount

        if remaining <= 0:
            raise HTTPException(
                status_code=409,
                detail="Tagihan sudah lunas",
            )

        if payment_amount > remaining:
            raise HTTPException(
                status_code=400,
                detail="Nominal pembayaran melebihi sisa tagihan",
            )

        now = paid_at or datetime.utcnow()
        new_paid_amount = paid_amount + payment_amount

        payment = Payment(
            billing_id=billing.id,
            payment_method_id=payment_method.id,
            amount=payment_amount,
            status="success",
            reference_number=ref_clean,
            paid_at=now,
        )

        self._sync_billing_status(
            billing,
            new_paid_amount,
            as_of_date or date.today(),
        )

        try:
            self.db.add(payment)
            self._send_receipt_email_simulation(
                nim=billing.nim,
                billing_id=billing.id,
                amount=payment_amount,
                reference_number=ref_clean,
                billing_status=billing.status,
            )
            self.db.commit()
            self.db.refresh(payment)

            return {
                "message": "Pembayaran berhasil diproses",
                "payment_id": payment.id,
                "billing_id": billing.id,
                "payment_method": payment_method.name,
                "reference_number": payment.reference_number,
                "amount": str(payment.amount),
                "total_paid": str(new_paid_amount),
                "remaining_amount": str(max(Decimal("0.00"), total_tagihan - new_paid_amount)),
                "payment_status": payment.status,
                "billing_status": billing.status,
                "paid_at": str(payment.paid_at),
                "receipt_sent": True,
            }
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Nomor referensi pembayaran sudah digunakan",
            )
        except Exception:
            self.db.rollback()
            raise

    def handle_webhook(
        self,
        payload: dict,
        signature: Optional[str] = None,
    ):
        """
        Menangani webhook konfirmasi pembayaran dari payment gateway (simulasi):
        1. Verifikasi HMAC signature
        2. Ekstrak transaction_id, billing_id, amount, status, method
        3. Validasi transaksi & pastikan idempotency
        4. Panggil process_payment & kirim receipt via email (simulasi log)
        """
        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=400,
                detail="Payload webhook tidak valid",
            )

        provided_sig = signature or payload.get("signature")
        canonical_data = {
            k: v for k, v in payload.items() if k != "signature"
        }
        canonical_str = json.dumps(
            canonical_data,
            separators=(",", ":"),
            sort_keys=True,
        )

        if not verify_webhook_signature(canonical_str, str(provided_sig or "")):
            raise HTTPException(
                status_code=401,
                detail="Signature webhook tidak valid",
            )

        transaction_id = str(payload.get("transaction_id") or "").strip()
        billing_id = payload.get("billing_id")
        amount = payload.get("amount")
        tx_status = str(payload.get("status") or "").strip().lower()
        method = payload.get("method") or "WEBHOOK_GATEWAY"

        if not transaction_id or billing_id is None or amount is None or not tx_status:
            raise HTTPException(
                status_code=400,
                detail="Payload webhook wajib memuat transaction_id, billing_id, amount, dan status",
            )

        if tx_status not in ("success", "paid", "settlement"):
            raise HTTPException(
                status_code=400,
                detail=f"Status transaksi webhook tidak dapat diproses sebagai pelunasan: {tx_status}",
            )

        result = self.process_payment(
            billing_id=int(billing_id),
            amount=amount,
            method=method,
            reference_number=transaction_id,
        )

        return {
            "webhook_status": "OK",
            "transaction_id": transaction_id,
            **result,
        }

    def create_payment(
        self,
        billing_id: int,
        payment_method_id: int,
        amount,
    ):
        billing = self._get_billing(billing_id)
        method = self._get_payment_method(payment_method_id)
        payment_amount = self._normalize_amount(amount)

        paid_amount = self._get_total_amount(
            billing.id,
            ["success"],
        )

        pending_amount = self._get_total_amount(
            billing.id,
            ["pending"],
        )

        outstanding = (
            Decimal(str(billing.amount))
            - paid_amount
            - pending_amount
        )

        if outstanding <= 0:
            raise HTTPException(
                status_code=409,
                detail="Tagihan sudah lunas atau seluruh sisa tagihan sedang diproses",
            )

        if payment_amount > outstanding:
            raise HTTPException(
                status_code=400,
                detail="Nominal pembayaran melebihi sisa tagihan",
            )

        payment = Payment(
            billing_id=billing.id,
            payment_method_id=method.id,
            amount=payment_amount,
            status="pending",
        )

        try:
            self.db.add(payment)
            self.db.commit()
            self.db.refresh(payment)

            return {
                "message": "Transaksi pembayaran berhasil dibuat",
                "payment_id": payment.id,
                "billing_id": payment.billing_id,
                "payment_method": method.name,
                "amount": str(payment.amount),
                "status": payment.status,
            }

        except Exception:
            self.db.rollback()
            raise

    def confirm_payment(
        self,
        payment_id: int,
        reference_number: str,
        paid_at: datetime = None,
        as_of_date: date = None,
    ):
        if not isinstance(reference_number, str):
            raise HTTPException(
                status_code=400,
                detail="Nomor referensi tidak valid",
            )

        reference_number = reference_number.strip()

        if not reference_number or len(reference_number) > 100:
            raise HTTPException(
                status_code=400,
                detail="Nomor referensi wajib diisi dan maksimal 100 karakter",
            )

        payment = self._get_payment(payment_id)

        if payment.status == "success":
            if payment.reference_number == reference_number:
                return {
                    "message": "Pembayaran sudah dikonfirmasi",
                    "payment_id": payment.id,
                    "status": payment.status,
                    "idempotent": True,
                }

            raise HTTPException(
                status_code=409,
                detail="Pembayaran sudah dikonfirmasi dengan referensi berbeda",
            )

        if payment.status != "pending":
            raise HTTPException(
                status_code=409,
                detail="Hanya pembayaran pending yang dapat dikonfirmasi",
            )

        duplicate = (
            self.db.query(Payment)
            .filter(
                Payment.reference_number == reference_number,
                Payment.id != payment.id,
            )
            .first()
        )

        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="Nomor referensi pembayaran sudah digunakan",
            )

        billing = self._get_billing(payment.billing_id)

        paid_amount = self._get_total_amount(
            billing.id,
            ["success"],
        )

        new_paid_amount = (
            paid_amount + Decimal(str(payment.amount))
        )

        if new_paid_amount > Decimal(str(billing.amount)):
            raise HTTPException(
                status_code=409,
                detail="Konfirmasi pembayaran melebihi total tagihan",
            )

        now = paid_at or datetime.utcnow()

        payment.status = "success"
        payment.reference_number = reference_number
        payment.paid_at = now

        self._sync_billing_status(
            billing,
            new_paid_amount,
            as_of_date or date.today(),
        )

        try:
            self._send_receipt_email_simulation(
                nim=billing.nim,
                billing_id=billing.id,
                amount=Decimal(str(payment.amount)),
                reference_number=reference_number,
                billing_status=billing.status,
            )
            self.db.commit()
            self.db.refresh(payment)

            return {
                "message": "Pembayaran berhasil dikonfirmasi",
                "payment_id": payment.id,
                "billing_id": billing.id,
                "reference_number": payment.reference_number,
                "amount": str(payment.amount),
                "payment_status": payment.status,
                "billing_status": billing.status,
                "paid_at": str(payment.paid_at),
            }

        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Nomor referensi pembayaran sudah digunakan",
            )

        except Exception:
            self.db.rollback()
            raise

    def fail_payment(
        self,
        payment_id: int,
        as_of_date: date = None,
    ):
        payment = self._get_payment(payment_id)

        if payment.status == "failed":
            return {
                "message": "Pembayaran sudah berstatus gagal",
                "payment_id": payment.id,
                "status": payment.status,
                "idempotent": True,
            }

        if payment.status != "pending":
            raise HTTPException(
                status_code=409,
                detail="Hanya pembayaran pending yang dapat dinyatakan gagal",
            )

        billing = self._get_billing(payment.billing_id)

        paid_amount = self._get_total_amount(
            billing.id,
            ["success"],
        )

        payment.status = "failed"

        self._sync_billing_status(
            billing,
            paid_amount,
            as_of_date,
        )

        try:
            self.db.commit()
            self.db.refresh(payment)

            return {
                "message": "Pembayaran ditandai gagal",
                "payment_id": payment.id,
                "billing_id": billing.id,
                "payment_status": payment.status,
                "billing_status": billing.status,
            }

        except Exception:
            self.db.rollback()
            raise
