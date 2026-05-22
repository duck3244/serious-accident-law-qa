"""FastAPI 요청/응답 스키마 (Pydantic 모델)"""
from typing import Any

from pydantic import BaseModel, Field


class QARequest(BaseModel):
    """법률 QA 요청"""
    question: str = Field(..., min_length=1, description="사용자 질문")
    use_rag: bool = Field(True, description="RAG(법조문 검색) 사용 여부")


class Source(BaseModel):
    """답변 근거가 된 법조문"""
    article: str
    title: str


class QAResponse(BaseModel):
    """법률 QA 응답"""
    question: str
    answer: str
    sources: list[Source]
    method: str


class ReviewTextRequest(BaseModel):
    """텍스트 문서 검토 요청"""
    document_text: str = Field(..., min_length=1, description="검토할 문서 내용")


class ReviewResponse(BaseModel):
    """문서 검토 응답"""
    report: str
    results: dict[str, Any]


class HealthResponse(BaseModel):
    """헬스 체크 응답"""
    status: str
    model_loaded: bool
