"""중대재해처벌법 QA 시스템 — FastAPI 백엔드 엔트리

실행 (backend/ 디렉터리에서):
    uvicorn main:app --port 8000

모델 로딩이 무겁기 때문에 개발 중에도 --reload 사용은 권장하지 않는다
(코드 변경 시마다 모델이 재로딩됨 — docs/TECH_REVIEW.md 3.4 참고).
"""
import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from integrated_qa import IntegratedQASystem
from routers import qa, review
from schemas import HealthResponse

LAW_DATA_FILE = "law_data.json"
QA_DATASET_FILE = "qa_dataset.json"


def _ensure_law_data() -> None:
    """법령 데이터 파일이 없으면 생성한다."""
    if os.path.exists(LAW_DATA_FILE):
        return
    print("법령 데이터가 없어 생성합니다...")
    from data_collector import LawDataCollector

    collector = LawDataCollector()
    content = collector.fetch_law_content()
    collector.parse_law_structure(content)
    collector.save_data(LAW_DATA_FILE)
    qa_pairs = collector.create_qa_dataset()
    collector.save_qa_dataset(qa_pairs, QA_DATASET_FILE)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작 시 모델을 1회 로드하고, 종료 시 정리한다."""
    print("=" * 60)
    print("백엔드 시작 — 모델 로딩 중 (수십 초 소요될 수 있음)...")
    _ensure_law_data()

    qa_system = IntegratedQASystem(use_finetuned=False)
    # 법령 인덱스가 비어 있으면 인덱싱
    if qa_system.rag.collection.count() == 0:
        qa_system.rag.load_and_index_law(LAW_DATA_FILE)

    app.state.qa = qa_system
    app.state.infer_lock = asyncio.Lock()
    print("모델 로딩 완료 — API 준비됨")
    print("=" * 60)
    yield
    # 종료 시 정리
    app.state.qa = None


app = FastAPI(
    title="중대재해처벌법 QA API",
    description="법률 질의응답 및 안전보건 문서 검토 백엔드",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(qa.router)
app.include_router(review.router)


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """헬스 체크 — 모델 로드 여부를 반환한다."""
    loaded = getattr(app.state, "qa", None) is not None
    return HealthResponse(
        status="ok" if loaded else "loading", model_loaded=loaded
    )
