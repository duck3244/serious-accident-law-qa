"""
Llama-3.2-Korean Fine-tuning for 중대재해처벌법 QA
LoRA 방식을 사용하여 효율적으로 학습
"""
import os
import json
import torch
from datasets import Dataset, load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
    BitsAndBytesConfig
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
    TaskType
)

class LawQAFineTuner:
    """중대재해처벌법 QA Fine-tuning"""
    
    def __init__(
        self,
        model_name: str = "torchtorchkimtorch/Llama-3.2-Korean-GGACHI-1B-Instruct-v1",
        output_dir: str = "./finetuned_model"
    ):
        self.model_name = model_name
        self.output_dir = output_dir
        self.use_cuda = torch.cuda.is_available()
        self.device = "cuda" if self.use_cuda else "cpu"

        print(f"사용 디바이스: {self.device}")
        if not self.use_cuda:
            print("⚠️  GPU가 감지되지 않았습니다. 4-bit 양자화 학습은 CUDA가 필요하므로 "
                  "CPU에서는 fine-tuning을 권장하지 않습니다(매우 느리거나 실패할 수 있음).")

        # 4-bit quantization 설정 (메모리 효율성) — CUDA 환경에서만 사용
        self.bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        ) if self.use_cuda else None
        
    def load_model_and_tokenizer(self):
        """모델 및 토크나이저 로드"""
        print("모델 및 토크나이저 로딩 중...")
        
        # 토크나이저 로드
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True
        )
        
        # 패딩 토큰 설정
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
        
        # 모델 로드 (CUDA 환경에서는 4-bit quantization 적용)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=self.bnb_config,
            device_map="auto" if self.use_cuda else None,
            trust_remote_code=True
        )

        # k-bit training 준비 (양자화 모델에 한함)
        if self.use_cuda:
            self.model = prepare_model_for_kbit_training(self.model)
        
        print("모델 로딩 완료!")
        
    def setup_lora(self):
        """LoRA 설정"""
        print("LoRA 설정 중...")
        
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=16,  # LoRA rank
            lora_alpha=32,
            lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            bias="none",
        )
        
        self.model = get_peft_model(self.model, lora_config)
        self.model.print_trainable_parameters()
        
    def prepare_dataset(self, qa_file: str = "qa_dataset.json"):
        """데이터셋 준비"""
        print(f"데이터셋 로딩: {qa_file}")
        
        # QA 데이터 로드
        with open(qa_file, 'r', encoding='utf-8') as f:
            qa_data = json.load(f)
        
        # 프롬프트 포맷팅
        formatted_data = []
        for item in qa_data:
            # Instruction format
            prompt = f"""### 지시사항:
{item['instruction']}

### 입력:
{item['input'] if item['input'] else '없음'}

### 응답:
{item['output']}"""
            
            formatted_data.append({"text": prompt})
        
        # Dataset 생성
        dataset = Dataset.from_list(formatted_data)
        
        # 토큰화
        def tokenize_function(examples):
            tokenized = self.tokenizer(
                examples["text"],
                padding="max_length",
                truncation=True,
                max_length=512,
                return_tensors="pt"
            )
            tokenized["labels"] = tokenized["input_ids"].clone()
            return tokenized
        
        tokenized_dataset = dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=dataset.column_names
        )
        
        # Train/Validation 분할
        split_dataset = tokenized_dataset.train_test_split(test_size=0.1)
        
        print(f"학습 데이터: {len(split_dataset['train'])}개")
        print(f"검증 데이터: {len(split_dataset['test'])}개")
        
        return split_dataset
    
    def train(self, dataset, epochs: int = 3):
        """모델 학습"""
        print("학습 시작...")
        
        training_args = TrainingArguments(
            output_dir=self.output_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=2,
            per_device_eval_batch_size=2,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            fp16=self.use_cuda,  # fp16은 CUDA 전용
            save_strategy="epoch",
            eval_strategy="epoch",  # transformers 4.41+ 명칭 (구 evaluation_strategy)
            logging_steps=10,
            warmup_steps=50,
            save_total_limit=2,
            load_best_model_at_end=True,
            report_to="none",
            # paged_adamw_8bit은 bitsandbytes(CUDA) 필요 → CPU는 표준 옵티마이저 사용
            optim="paged_adamw_8bit" if self.use_cuda else "adamw_torch",
        )
        
        # Data Collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False
        )
        
        # Trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=dataset["train"],
            eval_dataset=dataset["test"],
            data_collator=data_collator,
        )
        
        # 학습 실행
        trainer.train()
        
        # 모델 저장
        trainer.save_model(self.output_dir)
        self.tokenizer.save_pretrained(self.output_dir)
        
        print(f"학습 완료! 모델 저장 위치: {self.output_dir}")
        
    def test_inference(self, test_question: str):
        """추론 테스트"""
        print(f"\n테스트 질문: {test_question}")
        
        prompt = f"""### 지시사항:
{test_question}

### 입력:
없음

### 응답:
"""
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"\n모델 응답:\n{response}")
        
        return response

def main():
    # Fine-tuner 초기화
    finetuner = LawQAFineTuner()
    
    # 모델 로드
    finetuner.load_model_and_tokenizer()
    
    # LoRA 설정
    finetuner.setup_lora()
    
    # 데이터셋 준비
    dataset = finetuner.prepare_dataset()
    
    # 학습
    finetuner.train(dataset, epochs=3)
    
    # 테스트
    test_questions = [
        "중대재해처벌법의 목적은 무엇인가요?",
        "중대산업재해의 정의를 설명해주세요.",
        "경영책임자가 처벌받는 경우는 언제인가요?"
    ]
    
    for question in test_questions:
        finetuner.test_inference(question)
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()
