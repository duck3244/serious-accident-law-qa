#!/bin/bash

# 중대재해처벌법 QA 시스템 — FastAPI 백엔드 실행 스크립트

echo "================================================"
echo "중대재해처벌법 QA 및 문서 검토 시스템 (백엔드)"
echo "================================================"
echo ""

# Fine-tuned 모델 안내 (없어도 기본 모델로 동작)
if [ ! -d "finetuned_model" ]; then
    echo "ℹ️  Fine-tuned 모델이 없어 기본 모델로 시작합니다."
    echo "   Fine-tuning을 원하시면: python finetune.py"
    echo ""
fi

# 법령 데이터 생성 및 RAG 인덱싱은 main.py의 lifespan에서 자동 수행됩니다.
echo "🚀 FastAPI 백엔드 시작 중 (모델 로딩에 수십 초 소요)..."
echo ""
echo "API 문서:  http://localhost:8000/docs"
echo "헬스 체크: http://localhost:8000/api/health"
echo ""
echo "종료하려면 Ctrl+C를 누르세요."
echo ""

# FastAPI 앱 실행 (모델 로딩이 무거우므로 --reload 미사용)
uvicorn main:app --host 0.0.0.0 --port 8000
