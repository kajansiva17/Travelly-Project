"""Monthly Owner report (owner decision 13 Nov 2026; built in app/services/owner_report.py).

    GET /owners/me/reports/monthly/{YYYY-MM}       the report as JSON (on-screen preview)
    GET /owners/me/reports/monthly/{YYYY-MM}/pdf   the same report as a PDF download (English, A4)
    GET /admin/reports/monthly/{YYYY-MM}           the whole-platform Admin report as JSON (app/services/admin_report.py)
    GET /admin/reports/monthly/{YYYY-MM}/pdf       the same as a PDF

Approved Owners only; one Owner sees only their own vehicles, trips and money. Nothing is stored.
"""
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.api.routers.api import current, require_role
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.api.routers.review_api import admin
from app.services import admin_report, owner_report

router = APIRouter(prefix='/api/v1', tags=['reports'])


def period_of(period):
    if not re.fullmatch(r'\d{4}-\d{2}', period):
        raise ApiError(422, 'VALIDATION_ERROR', 'Use the month as YYYY-MM, for example 2026-11.')
    year, month = int(period[:4]), int(period[5:])
    today = datetime.now(ZoneInfo('Asia/Colombo')).date()
    if not 1 <= month <= 12 or year < 2020 or (year, month) > (today.year, today.month):
        raise ApiError(422, 'VALIDATION_ERROR', 'Choose a month from 2020 up to this month.')
    return year, month


@router.get('/owners/me/reports/monthly/{period}')
def monthly(period: str, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    year, month = period_of(period)
    request.app.state.store.rate(f'owner-report:{user.id}', 30, 600)
    return owner_report.build(db, user, year, month)


@router.get('/owners/me/reports/monthly/{period}/pdf')
async def monthly_pdf(period: str, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    year, month = period_of(period)
    request.app.state.store.rate(f'owner-report:{user.id}', 30, 600)
    data = await run_in_threadpool(owner_report.build, db, user, year, month)
    pdf = await run_in_threadpool(owner_report.render_pdf, data)
    return Response(pdf, media_type='application/pdf', headers={
        'Content-Disposition': f'attachment; filename="travelly-report-{period}.pdf"', 'Cache-Control': 'private, no-store'})


@router.get('/admin/reports/monthly/{period}')
def admin_monthly(period: str, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    year, month = period_of(period)
    request.app.state.store.rate(f'admin-report:{user.id}', 30, 600)
    return admin_report.build(db, year, month)


@router.get('/admin/reports/monthly/{period}/pdf')
async def admin_monthly_pdf(period: str, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    year, month = period_of(period)
    request.app.state.store.rate(f'admin-report:{user.id}', 30, 600)
    data = await run_in_threadpool(admin_report.build, db, year, month)
    pdf = await run_in_threadpool(admin_report.render_pdf, data)
    return Response(pdf, media_type='application/pdf', headers={
        'Content-Disposition': f'attachment; filename="travelly-admin-report-{period}.pdf"', 'Cache-Control': 'private, no-store'})
