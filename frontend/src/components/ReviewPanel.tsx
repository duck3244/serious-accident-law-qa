import { useState, type ReactNode } from 'react'
import { reviewFile, reviewText, type ReviewResponse } from '../api/client'

type Mode = 'text' | 'file'

const SAMPLE = `우리 회사의 안전보건 관리 현황

1. 안전관리자 1명 배치
2. 정기 안전교육 분기별 1회 실시
3. 작업장 안전점검 월 1회 실시

향후 계획:
- 추가 안전시설 설치 검토`

export default function ReviewPanel() {
  const [mode, setMode] = useState<Mode>('text')
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ReviewResponse | null>(null)

  const canSubmit = mode === 'text' ? text.trim().length > 0 : file !== null

  async function handleSubmit() {
    if (!canSubmit || loading) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res =
        mode === 'text'
          ? await reviewText(text)
          : await reviewFile(file as File)
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : '알 수 없는 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <ModeButton active={mode === 'text'} onClick={() => setMode('text')}>
          텍스트 입력
        </ModeButton>
        <ModeButton active={mode === 'file'} onClick={() => setMode('file')}>
          파일 업로드
        </ModeButton>
      </div>

      {mode === 'text' ? (
        <textarea
          className="w-full rounded-lg border border-slate-300 p-3 text-sm focus:border-blue-500 focus:outline-none"
          rows={10}
          placeholder={SAMPLE}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      ) : (
        <div className="rounded-lg border border-dashed border-slate-300 p-4">
          <input
            type="file"
            accept=".txt,.docx,.pdf"
            className="block w-full text-sm text-slate-600"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <p className="mt-2 text-xs text-slate-400">지원 형식: TXT, DOCX, PDF</p>
        </div>
      )}

      <button
        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        onClick={handleSubmit}
        disabled={loading || !canSubmit}
      >
        {loading ? '검토 중...' : '문서 검토'}
      </button>

      {error && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <pre className="overflow-x-auto rounded-lg bg-slate-900 p-4 text-xs leading-relaxed text-slate-100">
          {result.report}
        </pre>
      )}
    </div>
  )
}

function ModeButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        'rounded-lg px-3 py-1.5 text-sm font-medium transition ' +
        (active
          ? 'bg-slate-800 text-white'
          : 'bg-slate-100 text-slate-600 hover:bg-slate-200')
      }
    >
      {children}
    </button>
  )
}
