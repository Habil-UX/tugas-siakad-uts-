
from datetime import date
from decimal import Decimal
from unittest.mock import patch


# ==========================================
# BILLING ROUTER TESTS
# ==========================================

def test_generate_billing_route(client):
    with patch("app.routers.billing.BillingService") as mock_service:
        mock_service.return_value.generate_billing.return_value = {
            "message": "Tagihan berhasil dibuat"
        }

        response = client.post(
            "/api/billing/generate",
            json={
                "nim": "2026110001",
                "semester": 1,
                "tahun": "2026/2027",
                "semester_start_date": "2026-08-01"
            }
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Tagihan berhasil dibuat"
    mock_service.return_value.generate_billing.assert_called_once()


def test_calculate_late_fee_route(client):
    with patch("app.routers.billing.BillingService") as mock_service:
        mock_service.return_value.calculate_late_fee.return_value = {
            "billing_id": 1,
            "late_fee": "50000.00"
        }

        response = client.get(
            "/api/billing/1/late-fee",
            params={"as_of_date": "2026-11-15"}
        )

    assert response.status_code == 200
    assert response.json()["billing_id"] == 1
    mock_service.return_value.calculate_late_fee.assert_called_once_with(
        billing_id=1,
        as_of_date=date(2026, 11, 15)
    )


def test_update_billing_status_route(client):
    with patch("app.routers.billing.BillingService") as mock_service:
        mock_service.return_value.update_billing_status.return_value = {
            "billing_id": 1,
            "status": "paid"
        }

        response = client.put(
            "/api/billing/1/status",
            params={"as_of_date": "2026-11-15"}
        )

    assert response.status_code == 200
    assert response.json()["status"] == "paid"
    mock_service.return_value.update_billing_status.assert_called_once()


# ==========================================
# PAYMENT ROUTER TESTS
# ==========================================

def test_create_payment_route(client):
    with patch("app.routers.payment.PaymentService") as mock_service:
        mock_service.return_value.create_payment.return_value = {
            "payment_id": 1,
            "status": "pending"
        }

        response = client.post(
            "/api/payments/create",
            json={
                "billing_id": 1,
                "payment_method_id": 1,
                "amount": "1000000.00"
            }
        )

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    mock_service.return_value.create_payment.assert_called_once_with(
        billing_id=1,
        payment_method_id=1,
        amount=Decimal("1000000.00")
    )


def test_confirm_payment_route(client):
    with patch("app.routers.payment.PaymentService") as mock_service:
        mock_service.return_value.confirm_payment.return_value = {
            "payment_id": 1,
            "status": "success"
        }

        response = client.post(
            "/api/payments/1/confirm",
            json={
                "reference_number": "REF-ROUTER-001",
                "paid_at": "2026-11-15T10:00:00",
                "as_of_date": "2026-11-15"
            }
        )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_service.return_value.confirm_payment.assert_called_once()


def test_fail_payment_route(client):
    with patch("app.routers.payment.PaymentService") as mock_service:
        mock_service.return_value.fail_payment.return_value = {
            "payment_id": 1,
            "status": "failed"
        }

        response = client.post(
            "/api/payments/1/fail",
            json={
                "as_of_date": "2026-11-15"
            }
        )

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    mock_service.return_value.fail_payment.assert_called_once()
