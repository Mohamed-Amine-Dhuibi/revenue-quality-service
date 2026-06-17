"""HTTP routes: POST /analyse and GET /health."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from ..config import Settings, get_settings
from ..detection.parser import CsvValidationError, parse_csv
from ..detection.pipeline import run_analysis
from ..schemas import AnalyseResponse, ErrorResponse
from .security import require_api_key

router = APIRouter()


@router.get("/health", tags=["ops"], summary="Liveness probe (unauthenticated)")
def health() -> dict:
    return {"status": "ok"}


@router.post(
    "/analyse",
    response_model=AnalyseResponse,
    tags=["analysis"],
    summary="Analyse a bank-statement CSV and score revenue quality",
    dependencies=[Depends(require_api_key)],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or unparseable CSV"},
        401: {"model": ErrorResponse, "description": "Missing or invalid API key"},
        413: {"model": ErrorResponse, "description": "Uploaded file too large"},
    },
)
async def analyse(
    file: UploadFile = File(..., description="Bank-statement CSV."),
    borrower_name: str | None = Form(
        None,
        description="Optional borrower legal name; sharpens related-party detection "
        "on datasets without explicit intercompany markers.",
    ),
    settings: Settings = Depends(get_settings),
) -> AnalyseResponse:
    raw = await file.read()

    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_bytes} byte limit.",
        )
    if not raw.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty."
        )

    try:
        rows, parse_report = parse_csv(raw)
    except CsvValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    result = run_analysis(
        rows,
        parse_report,
        borrower_name=borrower_name,
        currency=settings.currency,
    )
    return AnalyseResponse(**result)
