"""
간단한 CLI 테스트 스크립트
데이터 생성 및 시스템 검증
"""
import os
import sys

def check_dependencies():
    """필수 패키지 확인"""
    print("📦 패키지 확인 중...")
    
    required_packages = [
        'torch',
        'transformers',
        'sentence_transformers',
        'chromadb',
        'gradio'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  다음 패키지를 설치해주세요:")
        print(f"  pip install {' '.join(missing)}")
        return False
    
    print("✅ 모든 필수 패키지가 설치되어 있습니다.\n")
    return True

def setup_data():
    """데이터 생성"""
    print("📝 데이터 생성 중...\n")
    
    from data_collector import LawDataCollector
    
    collector = LawDataCollector()
    
    # 법령 데이터 수집
    content = collector.fetch_law_content()
    law_data = collector.parse_law_structure(content)
    collector.save_data("law_data.json")
    
    # QA 데이터셋 생성
    qa_pairs = collector.create_qa_dataset()
    collector.save_qa_dataset(qa_pairs, "qa_dataset.json")
    
    print(f"✅ 데이터 생성 완료!\n")
    return True

def test_rag_system():
    """RAG 시스템 테스트"""
    print("🔍 RAG 시스템 테스트 중...\n")
    
    from rag_system import LawRAGSystem
    
    rag = LawRAGSystem()
    
    # 데이터 인덱싱
    if os.path.exists("law_data.json"):
        rag.load_and_index_law("law_data.json")
    
    # 검색 테스트
    query = "경영책임자의 의무"
    print(f"검색 쿼리: {query}\n")
    
    results = rag.search(query, top_k=2)
    
    for i, result in enumerate(results, 1):
        print(f"[{i}] 제{result['metadata']['article_num']}조 - {result['metadata']['article_title']}")
        print(f"    {result['document'][:100]}...\n")
    
    print("✅ RAG 시스템 테스트 완료!\n")
    return True

def test_qa_system():
    """QA 시스템 테스트"""
    print("💬 QA 시스템 테스트 중...\n")
    
    from integrated_qa import IntegratedQASystem
    
    # Base 모델만 사용 (Fine-tuned 모델이 없을 수 있음)
    qa_system = IntegratedQASystem(use_finetuned=False)
    
    # 질문 테스트
    test_question = "중대재해처벌법의 목적은 무엇인가요?"
    print(f"질문: {test_question}\n")
    
    result = qa_system.answer_question(test_question, use_rag=True)
    
    print(f"답변:\n{result['answer']}\n")
    
    if result['sources']:
        print("참고 법조문:")
        for source in result['sources']:
            print(f"  - 제{source['article']}조 ({source['title']})")
    
    print("\n✅ QA 시스템 테스트 완료!\n")
    return True

def main():
    """메인 함수"""
    print("="*60)
    print("중대재해처벌법 QA 시스템 - 초기 설정 및 테스트")
    print("="*60 + "\n")
    
    # 1. 패키지 확인
    if not check_dependencies():
        print("❌ 필수 패키지를 먼저 설치해주세요.")
        sys.exit(1)
    
    # 2. 데이터 생성
    if not os.path.exists("law_data.json"):
        if not setup_data():
            print("❌ 데이터 생성 실패")
            sys.exit(1)
    else:
        print("✅ 데이터 파일이 이미 존재합니다.\n")
    
    # 3. RAG 시스템 테스트
    try:
        if not test_rag_system():
            print("❌ RAG 시스템 테스트 실패")
            sys.exit(1)
    except Exception as e:
        print(f"❌ RAG 시스템 오류: {e}\n")
    
    # 4. QA 시스템 테스트
    try:
        if not test_qa_system():
            print("❌ QA 시스템 테스트 실패")
            sys.exit(1)
    except Exception as e:
        print(f"❌ QA 시스템 오류: {e}\n")
    
    print("="*60)
    print("🎉 모든 테스트 완료!")
    print("="*60 + "\n")
    
    print("다음 명령어로 웹 인터페이스를 실행할 수 있습니다:")
    print("  python app.py")
    print("\n또는:")
    print("  ./run.sh")
    print()

if __name__ == "__main__":
    main()
