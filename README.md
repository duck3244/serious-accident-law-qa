# 중대재해처벌법 QA 및 문서 검토 시스템

중대재해 처벌 등에 관한 법률에 대한 질의응답과 안전보건 문서 자동 검토를 제공하는 AI 시스템입니다.

## 주요 기능

### 1. 법률 QA (질의응답)
- 중대재해처벌법에 대한 자연어 질문에 답변
- Fine-tuned LLM + RAG 하이브리드 방식
- 관련 법조문 자동 참조 및 인용

### 2. 문서 검토
- 안전보건 관련 문서 자동 분석
- 중대재해처벌법 준수 여부 평가
- 미비점 도출 및 개선 권고사항 제시
- 관련 법조문 연결

### 3. 지원 형식
- 문서 업로드: TXT, DOCX, PDF
- 텍스트 직접 입력

---

## 빠른 시작

### 1단계: 패키지 설치

```bash
cd serious-accident-law-qa
pip install -r requirements.txt
```

**의존성 문제 발생 시:**
```bash
pip install "accelerate>=0.26.0"
pip install "pydantic>=2.0"
```

### 2단계: 시스템 검증 및 데이터 생성

```bash
python test_setup.py
```

이 스크립트가 자동으로:
- 필수 패키지 확인
- 법령 데이터 생성 (law_data.json)
- QA 데이터셋 생성 (qa_dataset.json)
- RAG 시스템 초기화 및 테스트
- QA 시스템 테스트

### 3단계: 웹 인터페이스 실행

**방법 1: 스크립트 사용 (추천)**
```bash
./run.sh
```

**방법 2: 직접 실행**
```bash
python app.py
```

**방법 3: Docker 사용**
```bash
docker-compose up
```

### 4단계: 접속

브라우저에서 접속:
```
http://localhost:7860
```

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                   사용자 인터페이스                    │
│                   (Gradio Web UI)                   │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│              통합 QA 시스템 (Integrated QA)           │
├─────────────────────────────────────────────────────┤
│  ┌──────────────────┐      ┌──────────────────┐    │
│  │  Fine-tuned LLM  │  +   │   RAG System     │    │
│  │   (LoRA 방식)     │      │  (Vector Search) │    │
│  └──────────────────┘      └──────────────────┘    │
└─────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌──────────────────┐          ┌──────────────────┐
│ Llama-3.2-Korean │          │    ChromaDB      │
│  GGACHI-1B       │          │   (법조문 임베딩)  │
└──────────────────┘          └──────────────────┘
```

## 기술 스택

### Core AI
- **Base Model**: Llama-3.2-Korean-GGACHI-1B-Instruct-v1
- **Fine-tuning**: LoRA (Low-Rank Adaptation) via PEFT
- **Framework**: PyTorch, Transformers

### RAG System
- **Vector Database**: ChromaDB
- **Embedding Model**: jhgan/ko-sroberta-multitask
- **Orchestration**: LangChain

### Web Interface
- **UI Framework**: Gradio
- **Document Processing**: python-docx, PyPDF2

---

## 사용 방법

### 법률 QA

1. "법률 QA" 탭 선택
2. 질문 입력 (예: "중대재해처벌법의 목적은 무엇인가요?")
3. "RAG 사용" 체크박스로 법조문 검색 활성화/비활성화
4. "답변 받기" 클릭
5. 답변 및 참고 법조문 확인

### 문서 검토

#### 파일 업로드 방식
1. "문서 검토 (파일)" 탭 선택
2. TXT, DOCX, PDF 파일 업로드
3. "문서 검토" 클릭
4. 검토 결과 확인

#### 텍스트 입력 방식
1. "문서 검토 (텍스트)" 탭 선택
2. 안전보건 관련 문서 내용 입력
3. "문서 검토" 클릭
4. 검토 결과 확인

---

## 검토 결과 해석

### 전체 준수율
- **80% 이상**: 우수
- **60-80%**: 보통 (개선 필요)
- **60% 미만**: 미흡 (긴급 개선 필요)

### 카테고리별 평가
1. **안전보건관리체계**: 인력, 예산, 체계 구축
2. **재해예방 대책**: 재발방지, 위험성 평가
3. **법령 준수**: 행정명령 이행, 법령 준수
4. **도급/용역 관리**: 협력업체 안전관리

### 제공 정보
- 미비점 목록
- 관련 법조문
- 개선 권고사항

---

## 예시 질문

```
- 중대재해처벌법의 목적은 무엇인가요?
- 중대산업재해의 정의는?
- 경영책임자의 안전보건 확보 의무는?
- 처벌 수준은 어떻게 되나요?
- 도급 관계에서도 책임을 져야 하나요?
- 양벌규정이란 무엇인가요?
- 중대시민재해란?
```

---

## 프로젝트 구조

```
serious-accident-law-qa/
├── app.py                  # Gradio 웹 인터페이스
├── data_collector.py       # 법령 데이터 수집 및 QA 데이터셋 생성
├── finetune.py             # Fine-tuning 스크립트
├── rag_system.py           # RAG 시스템 (검색 + 문서검토)
├── integrated_qa.py        # 통합 QA 시스템
├── test_setup.py           # 시스템 검증 스크립트
├── run.sh                  # 실행 스크립트
├── requirements.txt        # 필요 패키지 목록
├── Dockerfile              # Docker 설정
├── docker-compose.yml      # Docker Compose 설정
├── law_data.json           # 중대재해처벌법 조문 (생성됨)
├── qa_dataset.json         # QA 데이터셋 (생성됨)
├── sample_documents/       # 예제 문서
│   ├── 안전보건관리체계_가이드.txt
│   ├── 중대재해_사례분석.txt
│   ├── 경영책임자_의무사항.txt
│   └── qa_examples.json
├── finetuned_model/        # Fine-tuned 모델 (생성됨)
└── chroma_db/              # ChromaDB 저장소 (생성됨)
```

---

## 시스템 요구사항

### 최소 사양
- Python 3.8+
- RAM: 8GB
- 저장공간: 5GB

### 권장 사양
- Python 3.10+
- RAM: 16GB
- GPU: 8GB+ VRAM
- 저장공간: 10GB

---

## Fine-tuning (선택사항)

더 나은 성능을 원한다면:

```bash
python finetune.py
```

- 소요 시간: 1-2시간 (GPU 기준)
- GPU VRAM: 8GB 이상 권장
- CPU로도 가능하지만 매우 느림

### LoRA 설정
- **Rank (r)**: 16
- **Alpha**: 32
- **Dropout**: 0.05
- **Target Modules**: q_proj, k_proj, v_proj, o_proj

### 학습 설정
- **Epochs**: 3
- **Batch Size**: 2
- **Gradient Accumulation**: 4
- **Learning Rate**: 2e-4
- **Optimizer**: paged_adamw_8bit

### 메모리 최적화
- 4-bit Quantization (nf4)
- Gradient Checkpointing
- Mixed Precision Training (FP16)

---

## RAG 시스템 상세

### 임베딩
- **Model**: jhgan/ko-sroberta-multitask
- **차원**: 768
- **언어**: 한국어 특화

### 검색
- **Vector DB**: ChromaDB
- **유사도 측정**: Cosine Similarity
- **Top-K**: 3 (기본값)

### 인덱싱
- 중대재해처벌법 전체 조문
- 조문별 청크 분할
- 메타데이터: 조문 번호, 제목

---

## 트러블슈팅

### 패키지 설치 오류
```bash
# accelerate 버전 문제
pip install "accelerate>=0.26.0"

# pydantic 버전 문제
pip install "pydantic>=2.0"
```

### 모델 로딩 실패
```python
# app.py에서 use_finetuned=False로 설정
qa_system = IntegratedQASystem(use_finetuned=False)
```

### CUDA Out of Memory
- Batch size 줄이기
- Gradient accumulation 증가
- 4-bit quantization 활용

### ChromaDB 에러
```bash
rm -rf chroma_db/
python rag_system.py  # 재인덱싱
```

### ModuleNotFoundError
```bash
pip install -r requirements.txt
```

---

## 주의사항

1. **법률 자문 아님**: 본 시스템은 참고용이며 실제 법률 자문을 대체할 수 없습니다.

2. **GPU 권장**: Fine-tuning은 GPU 환경에서 실행을 권장합니다.

3. **모델 크기**:
   - Base Model: ~2.5GB
   - LoRA Adapters: ~50MB
   - 총 디스크 용량: ~5GB 필요

4. **메모리 요구사항**:
   - Fine-tuning: 8GB+ GPU VRAM
   - Inference only: 4GB+ GPU VRAM 또는 CPU 실행 가능

---

본 프로젝트는 교육 및 연구 목적으로 제작되었습니다.

---

**면책조항**: 본 시스템의 답변은 참고용이며, 법률 자문을 대체할 수 없습니다.
실제 법률 적용 시에는 반드시 전문가의 자문을 받으시기 바랍니다.
