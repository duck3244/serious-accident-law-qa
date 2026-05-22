/** FastAPI 백엔드 API 클라이언트
 *
 * 모든 요청은 상대 경로(/api/...)로 보낸다.
 * 개발 환경에서는 Vite 프록시가 이를 http://localhost:8000 으로 전달한다.
 */

export interface Source {
  article: string
  title: string
}

export interface QAResponse {
  question: string
  answer: string
  sources: Source[]
  method: string
}

export interface ReviewResponse {
  report: string
  results: Record<string, unknown>
}

/** 응답 상태를 확인하고 JSON을 파싱한다. 실패 시 detail 메시지로 Error를 던진다. */
async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `요청 실패 (HTTP ${res.status})`
    try {
      const body = await res.json()
      if (body?.detail) detail = String(body.detail)
    } catch {
      // JSON 파싱 실패는 무시하고 기본 메시지를 사용한다.
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

/** 법률 QA — 질문에 대한 답변을 요청한다. */
export async function askQuestion(
  question: string,
  useRag: boolean,
): Promise<QAResponse> {
  const res = await fetch('/api/qa', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, use_rag: useRag }),
  })
  return handle<QAResponse>(res)
}

/** 문서 검토 — 텍스트 입력. */
export async function reviewText(documentText: string): Promise<ReviewResponse> {
  const res = await fetch('/api/review/text', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_text: documentText }),
  })
  return handle<ReviewResponse>(res)
}

/** 문서 검토 — 파일 업로드(txt/docx/pdf). */
export async function reviewFile(file: File): Promise<ReviewResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/review/file', { method: 'POST', body: form })
  return handle<ReviewResponse>(res)
}

/** 헬스 체크 — 백엔드 모델 로드 여부를 반환한다. */
export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch('/api/health')
    if (!res.ok) return false
    const body = await res.json()
    return body?.model_loaded === true
  } catch {
    return false
  }
}
