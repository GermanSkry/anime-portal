import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import * as Sentry from '@sentry/react'
import './index.css'
import App from './App.jsx'
import { initAnalytics } from './services/analytics'

initAnalytics()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {/* a render crash used to leave a blank page and no trace anywhere */}
    <Sentry.ErrorBoundary fallback={
      <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
        Something went wrong. Please reload the page.
      </div>
    }>
      <App />
    </Sentry.ErrorBoundary>
  </StrictMode>,
)
