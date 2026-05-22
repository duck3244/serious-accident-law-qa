"""
통합 QA 시스템: Fine-tuned Model + RAG
"""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from rag_system import LawRAGSystem, DocumentReviewer

class IntegratedQASystem:
    """Fine-tuning + RAG 통합 시스템"""
    
    def __init__(
        self,
        base_model: str = "torchtorchkimtorch/Llama-3.2-Korean-GGACHI-1B-Instruct-v1",
        finetuned_model_path: str = "./finetuned_model",
        use_finetuned: bool = True
    ):
        """
        Args:
            base_model: 기본 모델 이름
            finetuned_model_path: Fine-tuned 모델 경로
            use_finetuned: Fine-tuned 모델 사용 여부
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"디바이스: {self.device}")
        
        # RAG 시스템 초기화
        print("RAG 시스템 로딩...")
        self.rag = LawRAGSystem()
        self.reviewer = DocumentReviewer(self.rag)
        
        # 언어 모델 로드
        print("언어 모델 로딩...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            base_model,
            trust_remote_code=True
        )
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        if use_finetuned:
            try:
                # Fine-tuned 모델 로드
                base = AutoModelForCausalLM.from_pretrained(
                    base_model,
                    torch_dtype=torch.float16,
                    device_map="auto",
                    trust_remote_code=True
                )
                self.model = PeftModel.from_pretrained(base, finetuned_model_path)
                print("Fine-tuned 모델 로드 완료!")
            except Exception as e:
                print(f"Fine-tuned 모델 로드 실패 ({type(e).__name__}: {e}). 기본 모델을 사용합니다.")
                self.model = AutoModelForCausalLM.from_pretrained(
                    base_model,
                    torch_dtype=torch.float16,
                    device_map="auto",
                    trust_remote_code=True
                )
        else:
            self.model = AutoModelForCausalLM.from_pretrained(
                base_model,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True
            )
        
        self.model.eval()
        print("시스템 준비 완료!\n")
    
    def answer_question(
        self,
        question: str,
        use_rag: bool = True,
        max_new_tokens: int = 512
    ) -> dict:
        """
        질문에 답변
        
        Args:
            question: 사용자 질문
            use_rag: RAG 사용 여부
            max_new_tokens: 생성할 최대 토큰 수
            
        Returns:
            답변 및 관련 정보
        """
        result = {
            "question": question,
            "answer": "",
            "sources": [],
            "method": "RAG + Fine-tuned Model" if use_rag else "Fine-tuned Model Only"
        }
        
        # RAG로 관련 문서 검색
        if use_rag:
            context = self.rag.get_context_for_query(question, top_k=3)
            sources = self.rag.search(question, top_k=3)
            result["sources"] = [
                {
                    "article": s['metadata']['article_num'],
                    "title": s['metadata']['article_title']
                }
                for s in sources
            ]
        else:
            context = ""
        
        # 프롬프트 구성
        if use_rag and context:
            prompt = f"""다음은 중대재해처벌법의 관련 조문입니다:

{context}

위 법조문을 참고하여 다음 질문에 답변해주세요.

### 질문:
{question}

### 답변:
"""
        else:
            prompt = f"""### 지시사항:
다음 질문에 중대재해처벌법에 근거하여 답변해주세요.

### 질문:
{question}

### 답변:
"""
        
        # 모델 추론
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
        
        # 응답 디코딩
        full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # 답변 부분만 추출
        if "### 답변:" in full_response:
            answer = full_response.split("### 답변:")[-1].strip()
        else:
            answer = full_response.replace(prompt, "").strip()
        
        result["answer"] = answer
        
        return result
    
    def review_document(self, document_text: str) -> dict:
        """
        문서 검토
        
        Args:
            document_text: 검토할 문서 내용
            
        Returns:
            검토 결과
        """
        review_results = self.reviewer.review_document(document_text)
        report = self.reviewer.generate_report(review_results)
        
        return {
            "results": review_results,
            "report": report
        }
    
    def chat(self):
        """대화형 인터페이스"""
        print("=" * 70)
        print("중대재해처벌법 QA 시스템")
        print("=" * 70)
        print("\n명령어:")
        print("  - 질문 입력: 중대재해처벌법에 대한 질문")
        print("  - 'review': 문서 검토 모드")
        print("  - 'quit': 종료")
        print("\n" + "=" * 70 + "\n")
        
        while True:
            user_input = input("📝 질문 또는 명령어: ").strip()
            
            if user_input.lower() in ['quit', 'exit', '종료']:
                print("시스템을 종료합니다.")
                break
            
            if user_input.lower() == 'review':
                print("\n검토할 문서 내용을 입력하세요 (입력 종료: 빈 줄 2번):")
                lines = []
                empty_count = 0
                while True:
                    line = input()
                    if line == "":
                        empty_count += 1
                        if empty_count >= 2:
                            break
                    else:
                        empty_count = 0
                        lines.append(line)
                
                document = "\n".join(lines)
                if document.strip():
                    result = self.review_document(document)
                    print("\n" + result["report"])
                continue
            
            if not user_input:
                continue
            
            # 질문 답변
            print("\n🤖 답변 생성 중...\n")
            result = self.answer_question(user_input, use_rag=True)
            
            print(f"💬 답변:\n{result['answer']}\n")
            
            if result['sources']:
                print("📚 참고 법조문:")
                for source in result['sources']:
                    print(f"  - 제{source['article']}조 ({source['title']})")
            
            print("\n" + "-" * 70 + "\n")

def main():
    # 통합 시스템 초기화
    qa_system = IntegratedQASystem(use_finetuned=False)  # Fine-tuned 모델이 없으면 False
    
    # 테스트 질문들
    test_questions = [
        "중대재해처벌법의 목적은 무엇인가요?",
        "경영책임자가 받는 처벌은 무엇인가요?",
        "도급 관계에서도 책임을 져야 하나요?",
        "중대산업재해의 기준이 무엇인가요?"
    ]
    
    print("="*70)
    print("자동 테스트")
    print("="*70 + "\n")
    
    for question in test_questions:
        print(f"📝 질문: {question}\n")
        result = qa_system.answer_question(question, use_rag=True)
        print(f"💬 답변:\n{result['answer']}\n")
        
        if result['sources']:
            print("📚 참고 법조문:")
            for source in result['sources']:
                print(f"  - 제{source['article']}조 ({source['title']})")
        
        print("\n" + "-"*70 + "\n")
    
    # 대화형 모드 (선택사항)
    # qa_system.chat()

if __name__ == "__main__":
    main()
