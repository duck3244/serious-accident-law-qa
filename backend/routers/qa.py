"""법률 QA 엔드포인트"""
from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool

from schemas import QARequest, QAResponse

router = APIRouter(prefix="/api", tags=["qa"])


@router.post("/qa", response_model=QAResponse)
async def answer_question(req: QARequest, request: Request) -> QAResponse:
    """질문에 대해 RAG + LLM으로 답변을 생성한다."""
    qa = request.app.state.qa
    # LLM 추론은 GPU를 점유하는 동기 작업 → 스레드풀에서 실행하고,
    # 단일 사용자라도 동시 호출이 겹치지 않도록 lock으로 직렬화한다.
    async with request.app.state.infer_lock:
        result = await run_in_threadpool(
            qa.answer_question, req.question, req.use_rag
        )
    return QAResponse(**result)
