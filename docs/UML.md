# UML 다이어그램 — 중대재해처벌법 QA 시스템

> 백엔드 핵심 클래스와 주요 시나리오를 UML로 표현한다.
> 다이어그램은 [Mermaid](https://mermaid.js.org/) 문법으로 작성되어 GitHub 등에서 렌더링된다.

---

## 1. 클래스 다이어그램

백엔드 도메인 클래스와 Pydantic 스키마의 구조 및 관계.

```mermaid
classDiagram
    class IntegratedQASystem {
        +str device
        +LawRAGSystem rag
        +DocumentReviewer reviewer
        +tokenizer
        +model
        +__init__(base_model, finetuned_model_path, use_finetuned)
        +answer_question(question, use_rag, max_new_tokens) dict
        +review_document(document_text) dict
        +chat() void
    }

    class LawRAGSystem {
        +embedder : SentenceTransformer
        +chroma_client : PersistentClient
        +collection
        +__init__(embedding_model, persist_directory)
        +load_and_index_law(law_file) void
        +search(query, top_k) List~Dict~
        +get_context_for_query(query, top_k) str
    }

    class DocumentReviewer {
        +LawRAGSystem rag
        +dict checklist_items
        +__init__(rag_system)
        +extract_keywords(document_text) List~str~
        +review_document(document_text) Dict
        +generate_report(review_results) str
    }

    class LawDataCollector {
        +str base_url
        +dict law_data
        +fetch_law_content() str
        +parse_law_structure(content) Dict
        +create_qa_dataset() List~Dict~
        +save_data(filename) void
        +save_qa_dataset(qa_pairs, filename) void
    }

    class LawQAFineTuner {
        +str model_name
        +str output_dir
        +bool use_cuda
        +bnb_config
        +load_model_and_tokenizer() void
        +setup_lora() void
        +prepare_dataset(qa_file) Dataset
        +train(dataset, epochs) void
        +test_inference(test_question) str
    }

    class FastAPI {
        <<framework>>
        +state.qa : IntegratedQASystem
        +state.infer_lock : asyncio.Lock
    }

    IntegratedQASystem *-- LawRAGSystem : 소유
    IntegratedQASystem *-- DocumentReviewer : 소유
    DocumentReviewer --> LawRAGSystem : 사용 (미비점 조문 검색)
    FastAPI --> IntegratedQASystem : app.state에 보관
    LawQAFineTuner ..> LawDataCollector : qa_dataset.json 소비
    IntegratedQASystem ..> LawQAFineTuner : finetuned_model 로드
```

### 1.1 Pydantic 스키마 (schemas.py)

```mermaid
classDiagram
    class QARequest {
        +str question
        +bool use_rag
    }
    class Source {
        +str article
        +str title
    }
    class QAResponse {
        +str question
        +str answer
        +List~Source~ sources
        +str method
    }
    class ReviewTextRequest {
        +str document_text
    }
    class ReviewResponse {
        +str report
        +dict results
    }
    class HealthResponse {
        +str status
        +bool model_loaded
    }

    QAResponse *-- Source : 포함
```

---

## 2. 컴포넌트 다이어그램

시스템의 모듈 단위 구성과 의존 방향.

```mermaid
flowchart TD
    subgraph Frontend["프론트엔드 (React + Vite)"]
        App[App.tsx]
        QaPanel[QaPanel.tsx]
        ReviewPanel[ReviewPanel.tsx]
        Client[api/client.ts]
        App --> QaPanel
        App --> ReviewPanel
        QaPanel --> Client
        ReviewPanel --> Client
    end

    subgraph Backend["백엔드 (FastAPI)"]
        Main[main.py]
        QaRouter[routers/qa.py]
        ReviewRouter[routers/review.py]
        Schemas[schemas.py]
        FileUtils[file_utils.py]
        Integrated[integrated_qa.py]
        Rag[rag_system.py]
        Collector[data_collector.py]

        Main --> QaRouter
        Main --> ReviewRouter
        Main --> Integrated
        Main --> Collector
        QaRouter --> Schemas
        ReviewRouter --> Schemas
        ReviewRouter --> FileUtils
        QaRouter --> Integrated
        ReviewRouter --> Integrated
        Integrated --> Rag
    end

    subgraph Storage["데이터 / 모델"]
        LawJson[(law_data.json)]
        QaJson[(qa_dataset.json)]
        Chroma[(ChromaDB)]
        FT[finetuned_model/]
    end

    Client -- "/api/* (Vite 프록시)" --> Main
    Collector --> LawJson
    Collector --> QaJson
    Rag --> Chroma
    Rag --> LawJson
    Integrated --> FT
```

---

## 3. 시퀀스 다이어그램 — 법률 QA

`POST /api/qa` 요청 처리 흐름.

```mermaid
sequenceDiagram
    actor User as 사용자
    participant QP as QaPanel.tsx
    participant API as api/client.ts
    participant R as routers/qa.py
    participant Lock as infer_lock
    participant QA as IntegratedQASystem
    participant RAG as LawRAGSystem
    participant DB as ChromaDB
    participant LLM as LLM (transformers)

    User->>QP: 질문 입력 + "답변 받기"
    QP->>API: askQuestion(question, useRag)
    API->>R: POST /api/qa
    R->>Lock: async with infer_lock
    R->>QA: run_in_threadpool(answer_question)

    alt use_rag = true
        QA->>RAG: search(question, top_k=3)
        RAG->>DB: query(query_embedding)
        DB-->>RAG: top-3 조문
        RAG-->>QA: sources + context
    end

    QA->>QA: 프롬프트 구성 (조문 컨텍스트 주입)
    QA->>LLM: model.generate(...)
    LLM-->>QA: 생성 텍스트
    QA->>QA: "### 답변:" 이후 추출
    QA-->>R: { question, answer, sources, method }
    R->>Lock: lock 해제
    R-->>API: QAResponse (JSON)
    API-->>QP: QAResponse
    QP-->>User: 답변 + 참고 법조문 표시
```

---

## 4. 시퀀스 다이어그램 — 문서 검토 (파일 업로드)

`POST /api/review/file` 요청 처리 흐름.

```mermaid
sequenceDiagram
    actor User as 사용자
    participant RP as ReviewPanel.tsx
    participant API as api/client.ts
    participant R as routers/review.py
    participant FU as file_utils.py
    participant QA as IntegratedQASystem
    participant DR as DocumentReviewer
    participant RAG as LawRAGSystem

    User->>RP: 파일 선택(txt/docx/pdf) + "문서 검토"
    RP->>API: reviewFile(file)
    API->>R: POST /api/review/file (multipart)
    R->>FU: extract_text(filename, data)

    alt 지원하지 않는 확장자
        FU-->>R: raise ValueError
        R-->>API: HTTP 415
    else 텍스트 추출 성공
        FU-->>R: document_text
        alt 빈 텍스트
            R-->>API: HTTP 422
        else
            R->>QA: run_in_threadpool(review_document)
            QA->>DR: review_document(document_text)
            DR->>DR: extract_keywords()
            DR->>DR: 카테고리별 체크리스트 매칭 → 점수 산출
            loop 미비점 상위 5개
                DR->>RAG: search(missing_item, top_k=1)
                RAG-->>DR: 관련 법조문
            end
            DR-->>QA: review_results
            QA->>DR: generate_report(review_results)
            DR-->>QA: report (텍스트)
            QA-->>R: { report, results }
            R-->>API: ReviewResponse (JSON)
            API-->>RP: ReviewResponse
            RP-->>User: 검토 리포트 표시
        end
    end
```

---

## 5. 시퀀스 다이어그램 — 애플리케이션 시작 (lifespan)

백엔드 부트스트랩 시 모델·인덱스 초기화 흐름.

```mermaid
sequenceDiagram
    participant Uvicorn
    participant Main as main.py (lifespan)
    participant Collector as LawDataCollector
    participant QA as IntegratedQASystem
    participant RAG as LawRAGSystem
    participant State as app.state

    Uvicorn->>Main: 앱 시작
    Main->>Main: _ensure_law_data()

    alt law_data.json 없음
        Main->>Collector: fetch / parse / save
        Collector-->>Main: law_data.json, qa_dataset.json 생성
    end

    Main->>QA: IntegratedQASystem(use_finetuned=False)
    QA->>RAG: 임베딩 모델 + ChromaDB 로드
    QA->>QA: LLM + 토크나이저 로드

    alt 인덱스 비어 있음 (collection.count() == 0)
        Main->>RAG: load_and_index_law(law_data.json)
        RAG-->>Main: 조문 인덱싱 완료
    end

    Main->>State: app.state.qa = qa_system
    Main->>State: app.state.infer_lock = asyncio.Lock()
    Main-->>Uvicorn: API 준비 완료 (yield)

    Note over Uvicorn,State: ── 요청 처리 구간 ──

    Uvicorn->>Main: 앱 종료
    Main->>State: app.state.qa = None
```

---

## 6. 상태 다이어그램 — 프론트엔드 헬스 상태

`App.tsx`의 백엔드 연결 상태 전이.

```mermaid
stateDiagram-v2
    [*] --> checking : 앱 마운트
    checking --> online : checkHealth() → model_loaded=true
    checking --> offline : checkHealth() → 실패 / false
    note right of online
        "백엔드 연결됨" 배지
    end note
    note right of offline
        "백엔드 오프라인" 배지
    end note
```

---

## 7. 유스케이스 다이어그램

```mermaid
flowchart LR
    User([사용자])
    Admin([운영자 / 개발자])

    UC1([법률 질문하기])
    UC2([RAG 사용 여부 선택])
    UC3([문서 텍스트 검토])
    UC4([문서 파일 업로드 검토])
    UC5([백엔드 연결 상태 확인])
    UC6([법령 데이터 수집])
    UC7([LLM 파인튜닝])

    User --> UC1
    User --> UC2
    User --> UC3
    User --> UC4
    User --> UC5
    Admin --> UC6
    Admin --> UC7

    UC1 -.includes.-> UC2
```
