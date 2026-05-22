import { useEffect, useState, type ReactNode } from 'react'
import { checkHealth } from './api/client'
import QaPanel from './components/QaPanel'
import ReviewPanel from './components/ReviewPanel'

type Tab = 'qa' | 'review'
type Health = 'checking' | 'online' | 'offline'

export default function App() {
  const [tab, setTab] = useState<Tab>('qa')
  const [health, setHealth] = useState<Health>('checking')

  useEffect(() => {
    let cancelled = false
    checkHealth().then((ok) => {
      if (!cancelled) setHealth(ok ? 'online' : 'offline')
    })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="bg-white shadow-sm">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-5">
          <div>
            <h1 className="text-xl font-bold text-slate-800">
              🏛️ 중대재해처벌법 QA 시스템
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              법률 질의응답 및 안전보건 문서 검토
            </p>
          </div>
          <HealthBadge health={health} />
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-6">
        <div className="mb-4 flex gap-2">
          <TabButton active={tab === 'qa'} onClick={() => setTab('qa')}>
            💬 법률 QA
          </TabButton>
          <TabButton active={tab === 'review'} onClick={() => setTab('review')}>
            📄 문서 검토
          </TabButton>
        </div>

        <div className="rounded-xl bg-white p-6 shadow-sm">
          {tab === 'qa' ? <QaPanel /> : <ReviewPanel />}
        </div>

        <p className="mt-6 text-center text-xs text-slate-400">
          본 시스템의 답변은 참고용이며 법률 자문을 대체하지 않습니다.
        </p>
      </main>
    </div>
  )
}

function HealthBadge({ health }: { health: Health }) {
  const config: Record<Health, { label: string; cls: string }> = {
    checking: { label: '연결 확인 중', cls: 'bg-slate-100 text-slate-500' },
    online: { label: '백엔드 연결됨', cls: 'bg-green-100 text-green-700' },
    offline: { label: '백엔드 오프라인', cls: 'bg-red-100 text-red-700' },
  }
  const { label, cls } = config[health]
  return (
    <span className={'rounded-full px-3 py-1 text-xs font-medium ' + cls}>
      {label}
    </span>
  )
}

function TabButton({
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
        'rounded-lg px-4 py-2 text-sm font-medium transition ' +
        (active
          ? 'bg-blue-600 text-white'
          : 'bg-white text-slate-600 hover:bg-slate-50')
      }
    >
      {children}
    </button>
  )
}
