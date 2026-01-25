#!/bin/bash

# 중대재해처벌법 QA 시스템 실행 스크립트

echo "================================================"
echo "중대재해처벌법 QA 및 문서 검토 시스템"
echo "================================================"
echo ""

# 데이터 파일 확인
if [ ! -f "law_data.json" ]; then
    echo "📝 법령 데이터 생성 중..."
    python data_collector.py
    echo "✅ 법령 데이터 생성 완료"
    echo ""
fi

# Fine-tuning 여부 확인
if [ ! -d "finetuned_model" ]; then
    echo "⚠️  Fine-tuned 모델이 없습니다."
    echo "Base 모델만 사용하여 시작합니다."
    echo ""
    echo "Fine-tuning을 원하시면 다음 명령어를 실행하세요:"
    echo "  python finetune.py"
    echo ""
fi

# RAG 시스템 확인
if [ ! -d "chroma_db" ]; then
    echo "🔍 RAG 시스템 초기화 중..."
    python -c "from rag_system import LawRAGSystem; import os; rag = LawRAGSystem(); rag.load_and_index_law() if os.path.exists('law_data.json') else None"
    echo "✅ RAG 시스템 초기화 완료"
    echo ""
fi

echo "🚀 웹 인터페이스 시작 중..."
echo ""
echo "브라우저에서 다음 주소로 접속하세요:"
echo "  http://localhost:7860"
echo ""
echo "종료하려면 Ctrl+C를 누르세요."
echo ""

# Gradio 앱 실행
python app.py
