"""문서 검토 엔드포인트 (텍스트 입력 / 파일 업로드)"""
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from file_utils import extract_text
from schemas import ReviewResponse, ReviewTextRequest

router = APIRouter(prefix="/api/review", tags=["review"])


@router.post("/text", response_model=ReviewResponse)
async def review_text(req: ReviewTextRequest, request: Request) -> ReviewResponse:
    """입력된 문서 텍스트를 중대재해처벌법 기준으로 검토한다."""
    qa = request.app.state.qa
    result = await run_in_threadpool(qa.review_document, req.document_text)
    return ReviewResponse(**result)


@router.post("/file", response_model=ReviewResponse)
async def review_file(
    request: Request, file: UploadFile = File(...)
) -> ReviewResponse:
    """업로드된 문서 파일(txt/docx/pdf)을 검토한다."""
    data = await file.read()

    try:
        document_text = extract_text(file.filename or "", data)
    except ValueError as e:
        # 415 Unsupported Media Type
        raise HTTPException(status_code=415, detail=str(e))

    if not document_text.strip():
        raise HTTPException(
            status_code=422, detail="파일에서 텍스트를 추출하지 못했습니다."
        )

    qa = request.app.state.qa
    result = await run_in_threadpool(qa.review_document, document_text)
    return ReviewResponse(**result)
