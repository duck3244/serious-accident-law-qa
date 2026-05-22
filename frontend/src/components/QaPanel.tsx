import { useState } from 'react'
import { askQuestion, type QAResponse } from '../api/client'

const EXAMPLES = [
  '중대재해처벌법의 목적은 무엇인가요?',
  '경영책임자의 의무는 무엇인가요?',
  '중대산업재해의 기준이 무엇인가요?',
]

export default function QaPanel() {
  const [question, setQuestion] = useState('')
  const [useRag, setUseRag] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<QAResponse | null>(null)

  async function handleSubmit() {
    if (!question.trim() || loading) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      setResult(await askQuestion(question, useRag))
    } catch (e) {
      setError(e instanceof Error ? e.message : '알 수 없는 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <textarea
        className="w-full rounded-lg border border-slate-300 p-3 text-sm focus:border-blue-500 focus:outline-none"
        rows={3}
        placeholder="예: 중대재해처벌법의 목적은 무엇인가요?"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
      />

      <div className="flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600 hover:bg-slate-200"
            onClick={() => setQuestion(ex)}
          >
            {ex}
          </button>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={useRag}
            onChange={(e) => setUseRag(e.target.checked)}
          />
          RAG 사용 (법조문 검색)
        </label>
        <button
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          onClick={handleSubmit}
          disabled={loading || !question.trim()}
        >
          {loading ? '답변 생성 중...' : '답변 받기'}
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-3">
          <div className="rounded-lg bg-slate-50 p-4">
            <h3 className="mb-2 text-sm font-semibold text-slate-700">답변</h3>
            <p className="whitespace-pre-wrap text-sm text-slate-800">
              {result.answer}
            </p>
          </div>
          {result.sources.length > 0 && (
            <div className="rounded-lg bg-blue-50 p-4">
              <h3 className="mb-2 text-sm font-semibold text-slate-700">
                참고 법조문
              </h3>
              <ul className="list-inside list-disc text-sm text-slate-700">
                {result.sources.map((s, i) => (
                  <li key={i}>
                    제{s.article}조 ({s.title})
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
