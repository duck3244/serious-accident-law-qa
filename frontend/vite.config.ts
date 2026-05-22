import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // dev 서버는 localhost에만 바인딩한다 (보안 — docs/TECH_REVIEW.md 부록 A-B).
    // 외부 노출이 필요해도 --host 플래그는 사용하지 않는다.
    host: 'localhost',
    port: 5173,
    proxy: {
      // /api 요청을 FastAPI 백엔드로 프록시 → 브라우저 입장에선 동일 출처, CORS 불필요
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
