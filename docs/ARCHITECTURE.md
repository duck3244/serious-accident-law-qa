# 아키텍처 문서 — 중대재해처벌법 QA 시스템

> 법률 질의응답(QA)과 안전보건 문서 검토를 제공하는 풀스택 애플리케이션.
> 한국어 LLM과 RAG(법조문 검색)를 결합하여 중대재해처벌법 기반 답변을 생성한다.

---

## 1. 개요

| 항목 | 내용 |
|------|------|
| 도메인 | 중대재해처벌법 법률 질의응답 / 문서 검토 |
| 백엔드 | Python 3.10 · FastAPI · uvicorn |
| 프론트엔드 | React 18 · TypeScript · Vite · Tailwind CSS |
| LLM | `Llama-3.2-Korean-GGACHI-1B-Instruct` (+ 선택적 LoRA 파인튜닝) |
| 임베딩 | `jhgan/ko-sroberta-multitask` (SentenceTransformers) |
| 벡터 DB | ChromaDB (PersistentClient, 디스크 영속화) |
| 배포 | Docker / docker-compose (GPU 예약) |

이 시스템은 두 가지 핵심 기능을 제공한다.

1. **법률 QA** — 사용자의 질문에 대해 RAG로 관련 법조문을 검색하고, LLM이 그 조문을 근거로 답변을 생성한다.
2. **문서 검토** — 입력 텍스트 또는 업로드 파일(txt/docx/pdf)을 체크리스트 기반으로 분석하여 준수율과 미비점 리포트를 생성한다.

---

## 2. 시스템 구성도

```
┌─────────────────────────────────────────────────────────────┐
│                         브라우저 (사용자)                       │
│  React SPA  ──  QaPanel · ReviewPanel · HealthBadge          │
└───────────────────────────┬─────────────────────────────────┘
                            │  /api/* (상대 경로)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Vite Dev Server (localhost:5173)                │
│              프록시: /api → http://localhost:8000             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI 백엔드 (localhost:8000)               │
│                                                               │
│   main.py (lifespan: 모델 1회 로드, app.state 보관)            │
│      │                                                        │
│      ├── routers/qa.py        POST /api/qa                    │
│      ├── routers/review.py    POST /api/review/text|file      │
│      └── /api/health          GET                             │
│                            │                                  │
│                            ▼                                  │
│            IntegratedQASystem (integrated_qa.py)              │
│              │                         │                      │
│              ▼                         ▼                      │
│      LawRAGSystem              DocumentReviewer                │
│      (rag_system.py)           (rag_system.py)                 │
│        │        │                                             │
│        ▼        ▼                                             │
│  SentenceTransformer   LLM (transformers + PEFT)               │
│        │                                                       │
│        ▼                                                       │
│   ChromaDB (./chroma_db)                                       │
└───────────────────────────────────────────────────────────────┘
```

---

## 3. 백엔드 아키텍처

### 3.1 계층 구조

| 계층 | 파일 | 책임 |
|------|------|------|
| 엔트리 / 부트스트랩 | `main.py` | FastAPI 앱 생성, lifespan에서 모델 1회 로드, 라우터 등록 |
| API 라우팅 | `routers/qa.py`, `routers/review.py` | HTTP 엔드포인트 정의, 동시성 제어 |
| 스키마 | `schemas.py` | Pydantic 요청/응답 모델 |
| 통합 서비스 | `integrated_qa.py` | LLM + RAG 오케스트레이션 (`IntegratedQASystem`) |
| 도메인 로직 | `rag_system.py` | 법조문 검색(`LawRAGSystem`), 문서 검토(`DocumentReviewer`) |
| 유틸리티 | `file_utils.py` | 업로드 파일에서 평문 텍스트 추출 |
| 데이터 준비 | `data_collector.py` | 법령 데이터/QA 데이터셋 생성 |
| 학습 | `finetune.py` | LoRA 기반 LLM 파인튜닝 (오프라인) |

### 3.2 핵심 컴포넌트

**`IntegratedQASystem`** — 시스템의 중심 오케스트레이터.
- 생성 시 임베딩 모델, LLM(파인튜닝 모델 또는 기본 모델), RAG 시스템을 모두 로드한다.
- `answer_question()` — RAG 컨텍스트를 프롬프트에 주입하고 LLM으로 답변 생성.
- `review_document()` — `DocumentReviewer`에 위임하여 검토 리포트 생성.

**`LawRAGSystem`** — 법조문 검색 엔진.
- `load_and_index_law()` — `law_data.json`을 조문 단위로 청킹·임베딩하여 ChromaDB에 인덱싱(중복 방지 가드 포함).
- `search()` / `get_context_for_query()` — 질의를 임베딩하여 유사 조문 top-k 검색.

**`DocumentReviewer`** — 규칙 기반 문서 검토기.
- 4개 카테고리(안전보건관리체계 / 재해예방 대책 / 법령 준수 / 도급·용역 관리) 체크리스트로 키워드 매칭.
- 카테고리별 준수율·전체 점수·미비점·관련 법조문·권고사항을 산출하고 텍스트 리포트로 변환.

### 3.3 모델 라이프사이클

LLM과 임베딩 모델 로딩은 수십 초가 소요되는 무거운 작업이다. 따라서:

- 모델은 FastAPI `lifespan`에서 **앱 시작 시 단 1회** 로드되어 `app.state.qa`에 보관된다.
- `--reload` 사용은 권장하지 않는다(코드 변경 시마다 모델 재로딩).
- `/api/health`는 `app.state.qa`의 존재 여부로 로딩 완료를 판단한다.

### 3.4 동시성 제어

- LLM 추론은 GPU를 점유하는 **동기·블로킹** 작업이다.
- `run_in_threadpool`로 이벤트 루프를 막지 않게 분리한다.
- `app.state.infer_lock`(asyncio.Lock)으로 QA 추론 호출을 **직렬화**하여 동시 호출이 GPU에서 겹치지 않게 한다.

---

## 4. 프론트엔드 아키텍처

| 파일 | 책임 |
|------|------|
| `main.tsx` | React 루트 마운트 |
| `App.tsx` | 탭 전환(QA / 검토), 헬스 체크, 레이아웃 |
| `components/QaPanel.tsx` | 질문 입력, RAG 토글, 답변·근거 조문 표시 |
| `components/ReviewPanel.tsx` | 텍스트/파일 모드 전환, 검토 리포트 표시 |
| `api/client.ts` | 백엔드 API 호출 래퍼 (`/api/*` 상대 경로) |

- 상태 관리는 React `useState`/`useEffect`만 사용 — 외부 상태 라이브러리 없음.
- 모든 API 요청은 상대 경로로 보내고, Vite 프록시가 백엔드로 전달하므로 **CORS 설정이 불필요**하다(브라우저 입장에서 동일 출처).
- 스타일링은 Tailwind 유틸리티 클래스.

---

## 5. 데이터 흐름

### 5.1 법률 QA 흐름

```
사용자 질문
   │
   ▼
QaPanel → askQuestion()  ──POST /api/qa──▶  routers/qa.py
                                               │ (infer_lock 획득)
                                               ▼
                              IntegratedQASystem.answer_question()
                                               │
                       ┌───────────────────────┴───────────────┐
                       ▼                                        ▼
            LawRAGSystem.search()                  프롬프트 구성 + LLM.generate()
            (질의 임베딩 → ChromaDB                  (법조문 컨텍스트 주입)
             top-3 조문 검색)                                    │
                       │                                        ▼
                       └──────────▶  { answer, sources, method } 응답
```

### 5.2 문서 검토 흐름

```
텍스트 입력 또는 파일 업로드
   │
   ▼
ReviewPanel → reviewText() / reviewFile()
   │
   ├─ 파일인 경우: routers/review.py → file_utils.extract_text()
   │                                   (txt/docx/pdf → 평문)
   ▼
IntegratedQASystem.review_document()
   │
   ▼
DocumentReviewer.review_document()
   │  · 키워드 추출
   │  · 카테고리별 체크리스트 매칭 → 준수율 산출
   │  · 미비점에 대한 관련 법조문 RAG 검색
   ▼
DocumentReviewer.generate_report() → { report, results } 응답
```

---

## 6. 데이터 저장소

| 저장소 | 위치 | 내용 |
|--------|------|------|
| 법령 데이터 | `law_data.json` | 장·조문 구조의 중대재해처벌법 데이터 |
| QA 데이터셋 | `qa_dataset.json` | 파인튜닝용 instruction/output 쌍 |
| 벡터 인덱스 | `./chroma_db/` | ChromaDB가 영속화한 조문 임베딩 (`law_articles` 컬렉션) |
| 파인튜닝 모델 | `./finetuned_model/` | LoRA 어댑터 가중치 (존재 시 로드) |
| 샘플 문서 | `sample_documents/` | 검토 기능 테스트용 예시 문서 |

부트스트랩 시 `law_data.json`이 없으면 `data_collector`가 생성하고, ChromaDB 컬렉션이 비어 있으면 자동 인덱싱한다.

---

## 7. 배포

- **개발**: 백엔드 `uvicorn main:app --port 8000`, 프론트엔드 `npm run dev`(Vite, localhost:5173).
- **컨테이너**: `backend/Dockerfile` + `docker-compose.yml`. NVIDIA GPU 1개를 예약하며 데이터 파일·`chroma_db`·`finetuned_model`을 볼륨 마운트한다.
- 보안상 Vite dev 서버는 `localhost`에만 바인딩한다(`--host` 미사용).

> ⚠️ 참고: `requirements.txt`의 `gradio`와 `Dockerfile`의 `CMD ["python", "app.py"]`는
> 레거시 Gradio 인터페이스 잔재이다. 현재 진입점은 `main.py`(FastAPI)이며 MVP 완료 후 정리 예정.

---

## 8. 외부 의존성

| 의존성 | 용도 |
|--------|------|
| `transformers`, `torch`, `peft`, `accelerate`, `bitsandbytes` | LLM 로딩·추론, LoRA, 4-bit 양자화 |
| `sentence-transformers` | 한국어 문장 임베딩 |
| `chromadb` | 벡터 검색 / 영속화 |
| `fastapi`, `uvicorn`, `python-multipart` | API 서버, 파일 업로드 |
| `python-docx`, `pypdf` | 업로드 문서 텍스트 추출 |
| `requests`, `beautifulsoup4`, `lxml` | 법령 데이터 수집 |
