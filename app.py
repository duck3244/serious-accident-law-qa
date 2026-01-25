"""
Gradio 웹 인터페이스
중대재해처벌법 QA 및 문서 검토 시스템
"""
import gradio as gr
import os
from integrated_qa import IntegratedQASystem
from docx import Document
import PyPDF2
import io

class WebInterface:
    """웹 인터페이스"""
    
    def __init__(self):
        """시스템 초기화"""
        print("시스템 초기화 중...")
        
        # 데이터가 없으면 생성
        if not os.path.exists("law_data.json"):
            print("법령 데이터 생성 중...")
            from data_collector import LawDataCollector
            collector = LawDataCollector()
            content = collector.fetch_law_content()
            law_data = collector.parse_law_structure(content)
            collector.save_data("law_data.json")
            qa_pairs = collector.create_qa_dataset()
            collector.save_qa_dataset(qa_pairs, "qa_dataset.json")
        
        # QA 시스템 로드
        self.qa_system = IntegratedQASystem(use_finetuned=False)
        
        # RAG 시스템에 데이터 인덱싱
        if self.qa_system.rag.collection.count() == 0:
            print("법령 데이터 인덱싱 중...")
            self.qa_system.rag.load_and_index_law("law_data.json")
        
        print("시스템 준비 완료!")
    
    def answer_question(self, question: str, use_rag: bool) -> tuple:
        """질문 답변"""
        if not question.strip():
            return "질문을 입력해주세요.", ""
        
        result = self.qa_system.answer_question(question, use_rag=use_rag)
        
        answer = result['answer']
        
        # 참고 법조문 정보
        sources_text = ""
        if result['sources']:
            sources_text = "📚 **참고 법조문:**\n\n"
            for source in result['sources']:
                sources_text += f"- 제{source['article']}조 ({source['title']})\n"
        
        return answer, sources_text
    
    def extract_text_from_file(self, file) -> str:
        """파일에서 텍스트 추출"""
        if file is None:
            return ""
        
        file_path = file.name
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            elif file_ext == '.docx':
                doc = Document(file_path)
                return '\n'.join([para.text for para in doc.paragraphs])
            
            elif file_ext == '.pdf':
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                    return text
            
            else:
                return "지원하지 않는 파일 형식입니다. (txt, docx, pdf만 지원)"
        
        except Exception as e:
            return f"파일 읽기 오류: {str(e)}"
    
    def review_document_from_file(self, file) -> str:
        """파일 업로드 후 문서 검토"""
        if file is None:
            return "파일을 업로드해주세요."
        
        # 파일에서 텍스트 추출
        document_text = self.extract_text_from_file(file)
        
        if not document_text or document_text.startswith("지원하지 않는") or document_text.startswith("파일 읽기"):
            return document_text
        
        # 문서 검토
        result = self.qa_system.review_document(document_text)
        return result['report']
    
    def review_document_from_text(self, document_text: str) -> str:
        """텍스트 입력 후 문서 검토"""
        if not document_text.strip():
            return "검토할 문서 내용을 입력해주세요."
        
        result = self.qa_system.review_document(document_text)
        return result['report']
    
    def create_interface(self):
        """Gradio 인터페이스 생성"""
        
        with gr.Blocks(title="중대재해처벌법 QA 시스템", theme=gr.themes.Soft()) as demo:
            gr.Markdown(
                """
                # 🏛️ 중대재해처벌법 QA 및 문서 검토 시스템
                
                **중대재해 처벌 등에 관한 법률**에 대한 질문 답변과 문서 검토를 제공합니다.
                """
            )
            
            with gr.Tabs():
                # 탭 1: QA 시스템
                with gr.Tab("💬 법률 QA"):
                    gr.Markdown("### 중대재해처벌법에 대해 궁금한 점을 물어보세요")
                    
                    with gr.Row():
                        with gr.Column(scale=2):
                            question_input = gr.Textbox(
                                label="질문",
                                placeholder="예: 중대재해처벌법의 목적은 무엇인가요?",
                                lines=3
                            )
                            use_rag_checkbox = gr.Checkbox(
                                label="RAG 사용 (법조문 검색 활성화)",
                                value=True
                            )
                            submit_btn = gr.Button("답변 받기", variant="primary")
                        
                        with gr.Column(scale=3):
                            answer_output = gr.Textbox(
                                label="답변",
                                lines=10,
                                interactive=False
                            )
                            sources_output = gr.Markdown(
                                label="참고 법조문"
                            )
                    
                    gr.Markdown("### 💡 질문 예시")
                    example_questions = [
                        ["중대재해처벌법의 목적은 무엇인가요?", True],
                        ["경영책임자의 의무는 무엇인가요?", True],
                        ["중대산업재해의 기준이 무엇인가요?", True],
                        ["도급 관계에서도 책임을 져야 하나요?", True],
                        ["처벌 수준은 어떻게 되나요?", True]
                    ]
                    
                    gr.Examples(
                        examples=example_questions,
                        inputs=[question_input, use_rag_checkbox],
                        outputs=[answer_output, sources_output],
                        fn=self.answer_question,
                        cache_examples=False
                    )
                    
                    submit_btn.click(
                        fn=self.answer_question,
                        inputs=[question_input, use_rag_checkbox],
                        outputs=[answer_output, sources_output]
                    )
                
                # 탭 2: 문서 검토 (파일 업로드)
                with gr.Tab("📄 문서 검토 (파일)"):
                    gr.Markdown(
                        """
                        ### 안전보건 관련 문서를 업로드하여 중대재해처벌법 준수 여부를 검토하세요
                        
                        **지원 형식:** TXT, DOCX, PDF
                        """
                    )
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            file_input = gr.File(
                                label="문서 업로드",
                                file_types=[".txt", ".docx", ".pdf"]
                            )
                            review_file_btn = gr.Button("문서 검토", variant="primary")
                        
                        with gr.Column(scale=2):
                            file_review_output = gr.Textbox(
                                label="검토 결과",
                                lines=20,
                                interactive=False
                            )
                    
                    review_file_btn.click(
                        fn=self.review_document_from_file,
                        inputs=file_input,
                        outputs=file_review_output
                    )
                
                # 탭 3: 문서 검토 (텍스트 입력)
                with gr.Tab("✏️ 문서 검토 (텍스트)"):
                    gr.Markdown("### 문서 내용을 직접 입력하여 검토하세요")
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            text_input = gr.Textbox(
                                label="문서 내용",
                                placeholder="검토할 안전보건 관련 문서 내용을 입력하세요...",
                                lines=15
                            )
                            review_text_btn = gr.Button("문서 검토", variant="primary")
                        
                        with gr.Column(scale=1):
                            text_review_output = gr.Textbox(
                                label="검토 결과",
                                lines=20,
                                interactive=False
                            )
                    
                    gr.Markdown("### 📝 샘플 문서")
                    sample_doc = """우리 회사의 안전보건 관리 현황

1. 조직 및 인력
   - 안전관리자 1명 배치
   - 보건관리자 미배치

2. 안전보건 활동
   - 정기 안전교육 분기별 1회 실시
   - 작업장 안전점검 월 1회 실시
   - 위험성 평가 미실시

3. 예산 및 시설
   - 안전보건 예산: 연간 500만원
   - 보호구 지급 현황: 안전모, 안전화
   - 안전시설: 소화기 10대

4. 향후 계획
   - 추가 안전시설 설치 검토
   - 안전교육 강화 계획"""
                    
                    gr.Examples(
                        examples=[[sample_doc]],
                        inputs=text_input,
                        outputs=text_review_output,
                        fn=self.review_document_from_text,
                        cache_examples=False
                    )
                    
                    review_text_btn.click(
                        fn=self.review_document_from_text,
                        inputs=text_input,
                        outputs=text_review_output
                    )
                
                # 탭 4: 시스템 정보
                with gr.Tab("ℹ️ 시스템 정보"):
                    gr.Markdown(
                        """
                        ## 시스템 구성
                        
                        ### 🤖 언어 모델
                        - **Base Model**: Llama-3.2-Korean-GGACHI-1B-Instruct-v1
                        - **Fine-tuning**: LoRA (Low-Rank Adaptation)
                        - **Dataset**: 중대재해처벌법 QA 데이터셋
                        
                        ### 🔍 RAG (Retrieval-Augmented Generation)
                        - **Vector DB**: ChromaDB
                        - **Embedding**: ko-sroberta-multitask (한국어 특화)
                        - **Indexed**: 중대재해처벌법 전체 조문
                        
                        ### 📋 문서 검토 기능
                        - 안전보건관리체계 점검
                        - 재해예방 대책 확인
                        - 법령 준수 현황 검토
                        - 도급/용역 관리 평가
                        
                        ### 💡 주요 기능
                        1. **법률 QA**: 중대재해처벌법 관련 질의응답
                        2. **문서 검토**: 안전보건 문서 자동 분석 및 미비점 도출
                        3. **법조문 참조**: 관련 법조문 자동 연결
                        4. **개선 권고**: 미비점에 대한 구체적 개선 방안 제시
                        
                        ---
                        
                        **개발 기술 스택**
                        - PyTorch, Transformers, PEFT
                        - LangChain, ChromaDB
                        - Sentence-Transformers
                        - Gradio
                        """
                    )
            
            gr.Markdown(
                """
                ---
                **주의사항**: 본 시스템의 답변은 참고용이며, 법률 자문을 대체할 수 없습니다. 
                실제 법률 적용 시에는 반드시 전문가의 자문을 받으시기 바랍니다.
                """
            )
        
        return demo
    
    def launch(self, share=False):
        """웹 인터페이스 실행"""
        demo = self.create_interface()
        demo.launch(share=share, server_name="0.0.0.0", server_port=7860)

def main():
    interface = WebInterface()
    interface.launch(share=False)

if __name__ == "__main__":
    main()
