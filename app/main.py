from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routers import (
    attendance,
    auth,
    billing,
    dashboard,
    grades,
    krs,
    payment,
    pmb,
    schedules,
)
from app.services.scheduler_service import billing_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    billing_scheduler.start()
    try:
        yield
    finally:
        billing_scheduler.shutdown()


app = FastAPI(
    title="Sistem Informasi Akademik",
    version="11.0",
    description="API Sistem Informasi Akademik Terintegrasi",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    return JSONResponse(
        status_code=400,
        content={"detail": jsonable_encoder(exc.errors())},
    )


# ==========================================
# ROUTER AUTENTIKASI & AKADEMIK
# ==========================================

app.include_router(auth.router)
app.include_router(grades.router)
app.include_router(pmb.router)
app.include_router(krs.router)
app.include_router(schedules.router)
app.include_router(dashboard.router)


# ==========================================
# ROUTER KEUANGAN MINGGU 11 & PRESENSI MINGGU 12
# ==========================================

app.include_router(billing.router)
app.include_router(payment.router)
app.include_router(attendance.router)


# ==========================================
# ROOT ENDPOINT
# ==========================================

@app.get("/")
def root():
    return {
        "message": "API Akademik dan Keuangan Terintegrasi.",
        "documentation": "/docs",
        "version": "11.0",
    }
