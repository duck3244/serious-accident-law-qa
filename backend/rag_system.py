"""
RAG (Retrieval-Augmented Generation) 시스템
중대재해처벌법 문서 검색 및 QA
"""
import os
import json
import logging
from typing import List, Dict
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

# chromadb 0.5.x 텔레메트리(posthog) 버전 충돌로 발생하는 콘솔 에러 노이즈 억제
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)

class LawRAGSystem:
    """중대재해처벌법 RAG 시스템"""
    
    def __init__(
        self,
        embedding_model: str = "jhgan/ko-sroberta-multitask",
        persist_directory: str = "./chroma_db"
    ):
        """
        Args:
            embedding_model: 한국어 임베딩 모델
            persist_directory: ChromaDB 저장 경로
        """
        print("RAG 시스템 초기화 중...")
        
        # 임베딩 모델 로드
        self.embedder = SentenceTransformer(embedding_model)
        print(f"임베딩 모델 로드 완료: {embedding_model}")
        
        # ChromaDB 클라이언트 초기화
        # PersistentClient를 써야 persist_directory에 실제로 디스크 영속화됨
        # (chromadb.Client는 in-memory 전용이라 재시작 시 인덱스가 사라짐)
        self.chroma_client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        # 컬렉션 생성/로드 (있으면 로드, 없으면 생성)
        self.collection = self.chroma_client.get_or_create_collection(
            name="law_articles",
            metadata={"description": "중대재해처벌법 조문"}
        )
        print(f"컬렉션 준비 완료 (기존 인덱싱 문서: {self.collection.count()}개)")
    
    def load_and_index_law(self, law_file: str = "law_data.json"):
        """법령 데이터 로드 및 인덱싱"""
        # 이미 인덱싱된 경우 중복 add 방지 (PersistentClient는 재실행 시 데이터가 남아있음)
        if self.collection.count() > 0:
            print(f"이미 {self.collection.count()}개 조문이 인덱싱되어 있어 건너뜁니다.")
            return

        print(f"법령 데이터 인덱싱: {law_file}")

        with open(law_file, 'r', encoding='utf-8') as f:
            law_data = json.load(f)
        
        documents = []
        metadatas = []
        ids = []
        
        # 조문별로 청크 생성
        for idx, article in enumerate(law_data.get("articles", [])):
            # 조문 내용 구성
            content = f"제{article['article_num']}조 ({article['article_title']})\n"
            content += article.get('content', '')
            
            for para in article.get('paragraphs', []):
                content += f"\n{para}"
            
            documents.append(content)
            metadatas.append({
                "article_num": article['article_num'],
                "article_title": article['article_title'],
                "type": "article"
            })
            ids.append(f"article_{idx}")
        
        # 임베딩 생성
        embeddings = self.embedder.encode(
            documents,
            show_progress_bar=True,
            convert_to_numpy=True
        ).tolist()
        
        # ChromaDB에 저장
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"{len(documents)}개 조문 인덱싱 완료!")
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        쿼리와 관련된 법조문 검색
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            
        Returns:
            검색 결과 리스트
        """
        # 쿼리 임베딩
        query_embedding = self.embedder.encode([query])[0].tolist()
        
        # 검색
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        # 결과 포맷팅
        formatted_results = []
        for i in range(len(results['documents'][0])):
            formatted_results.append({
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if 'distances' in results else None
            })
        
        return formatted_results
    
    def get_context_for_query(self, query: str, top_k: int = 3) -> str:
        """쿼리에 대한 컨텍스트 생성"""
        results = self.search(query, top_k)
        
        context = "관련 법조문:\n\n"
        for i, result in enumerate(results, 1):
            context += f"[{i}] {result['document']}\n\n"
        
        return context

class DocumentReviewer:
    """문서 검토 시스템"""
    
    def __init__(self, rag_system: LawRAGSystem):
        self.rag = rag_system
        
        # 체크리스트 항목 정의
        self.checklist_items = {
            "안전보건관리체계": [
                "재해예방에 필요한 인력 배치",
                "재해예방에 필요한 예산 확보",
                "안전보건관리체계 구축",
                "안전보건관리체계 이행 방안"
            ],
            "재해예방 대책": [
                "재해 발생 시 재발방지 대책 수립",
                "재발방지 대책 이행 계획",
                "위험성 평가 실시",
                "안전작업절차 수립"
            ],
            "법령 준수": [
                "중앙행정기관 시정명령 이행",
                "지방자치단체 개선명령 이행",
                "산업안전보건법 의무 이행",
                "관련 법령 준수 현황"
            ],
            "도급/용역 관리": [
                "도급업체 안전관리",
                "용역업체 안전보건 확보",
                "수급인 종사자 안전조치",
                "작업 위험요인 고지"
            ]
        }
    
    def extract_keywords(self, document_text: str) -> List[str]:
        """문서에서 키워드 추출"""
        keywords = []
        
        # 주요 키워드 리스트
        key_terms = [
            "안전보건", "재해예방", "위험성평가", "안전관리",
            "경영책임자", "사업주", "종사자", "안전조치",
            "예산", "인력", "교육", "훈련", "점검", "관리",
            "도급", "용역", "위탁", "수급인"
        ]
        
        for term in key_terms:
            if term in document_text:
                keywords.append(term)
        
        return keywords
    
    def review_document(self, document_text: str) -> Dict:
        """
        문서 검토 및 미비점 분석
        
        Args:
            document_text: 검토할 문서 내용
            
        Returns:
            검토 결과 딕셔너리
        """
        print("문서 검토 시작...")
        
        # 키워드 추출
        keywords = self.extract_keywords(document_text)
        
        # 카테고리별 체크
        review_results = {
            "overall_score": 0,
            "category_scores": {},
            "missing_items": [],
            "recommendations": [],
            "related_articles": []
        }
        
        total_items = 0
        found_items = 0
        
        for category, items in self.checklist_items.items():
            category_found = 0
            category_total = len(items)
            missing_in_category = []
            
            for item in items:
                total_items += 1
                # 간단한 키워드 매칭
                item_keywords = item.split()
                if any(keyword in document_text for keyword in item_keywords):
                    found_items += 1
                    category_found += 1
                else:
                    missing_in_category.append(item)
            
            category_score = (category_found / category_total) * 100
            review_results["category_scores"][category] = {
                "score": category_score,
                "found": category_found,
                "total": category_total,
                "missing": missing_in_category
            }
            
            if missing_in_category:
                review_results["missing_items"].extend([
                    f"[{category}] {item}" for item in missing_in_category
                ])
        
        # 전체 점수 계산
        review_results["overall_score"] = (found_items / total_items) * 100 if total_items > 0 else 0
        
        # 미비점에 대한 관련 법조문 검색
        for missing in review_results["missing_items"][:5]:  # 상위 5개만
            related = self.rag.search(missing, top_k=1)
            if related:
                review_results["related_articles"].append({
                    "missing_item": missing,
                    "related_article": related[0]['metadata']['article_num'],
                    "article_title": related[0]['metadata']['article_title']
                })
        
        # 개선 권고사항 생성
        if review_results["overall_score"] < 70:
            review_results["recommendations"].append(
                "전반적인 안전보건관리체계 보완이 필요합니다."
            )
        
        for category, score_info in review_results["category_scores"].items():
            if score_info["score"] < 50:
                review_results["recommendations"].append(
                    f"{category} 관련 조치사항을 보완해야 합니다."
                )
        
        return review_results
    
    def generate_report(self, review_results: Dict) -> str:
        """검토 결과 리포트 생성"""
        report = "=" * 60 + "\n"
        report += "중대재해처벌법 문서 검토 결과\n"
        report += "=" * 60 + "\n\n"
        
        # 전체 점수
        score = review_results["overall_score"]
        report += f"📊 전체 준수율: {score:.1f}%\n"
        
        if score >= 80:
            report += "✅ 평가: 우수\n\n"
        elif score >= 60:
            report += "⚠️  평가: 보통 (개선 필요)\n\n"
        else:
            report += "❌ 평가: 미흡 (긴급 개선 필요)\n\n"
        
        # 카테고리별 점수
        report += "📋 카테고리별 준수율:\n"
        report += "-" * 60 + "\n"
        for category, score_info in review_results["category_scores"].items():
            status = "✅" if score_info["score"] >= 70 else "⚠️"
            report += f"{status} {category}: {score_info['score']:.1f}% "
            report += f"({score_info['found']}/{score_info['total']})\n"
        report += "\n"
        
        # 미비점
        if review_results["missing_items"]:
            report += "🔍 미비점:\n"
            report += "-" * 60 + "\n"
            for i, item in enumerate(review_results["missing_items"], 1):
                report += f"{i}. {item}\n"
            report += "\n"
        
        # 관련 법조문
        if review_results["related_articles"]:
            report += "📖 관련 법조문:\n"
            report += "-" * 60 + "\n"
            for item in review_results["related_articles"]:
                report += f"• {item['missing_item']}\n"
                report += f"  → 제{item['related_article']}조 ({item['article_title']})\n\n"
        
        # 권고사항
        if review_results["recommendations"]:
            report += "💡 개선 권고사항:\n"
            report += "-" * 60 + "\n"
            for i, rec in enumerate(review_results["recommendations"], 1):
                report += f"{i}. {rec}\n"
            report += "\n"
        
        report += "=" * 60 + "\n"
        
        return report

def main():
    # RAG 시스템 초기화
    rag = LawRAGSystem()
    
    # 법령 데이터 인덱싱
    if os.path.exists("law_data.json"):
        rag.load_and_index_law()
    
    # 검색 테스트
    test_queries = [
        "경영책임자의 의무는 무엇인가요?",
        "중대산업재해 처벌 기준",
        "도급 관계에서의 책임"
    ]
    
    print("\n" + "="*60)
    print("검색 테스트")
    print("="*60 + "\n")
    
    for query in test_queries:
        print(f"질문: {query}")
        results = rag.search(query, top_k=2)
        for i, result in enumerate(results, 1):
            print(f"\n[{i}] 제{result['metadata']['article_num']}조")
            print(result['document'][:200] + "...")
        print("\n" + "-"*60 + "\n")
    
    # 문서 검토 테스트
    reviewer = DocumentReviewer(rag)
    
    sample_document = """
    우리 회사의 안전보건 관리 현황
    
    1. 안전관리자 1명 배치
    2. 정기 안전교육 실시
    3. 작업장 안전점검 월 1회 실시
    
    향후 계획:
    - 추가 안전시설 설치 검토
    """
    
    print("\n" + "="*60)
    print("문서 검토 테스트")
    print("="*60 + "\n")
    
    review_results = reviewer.review_document(sample_document)
    report = reviewer.generate_report(review_results)
    print(report)

if __name__ == "__main__":
    main()
