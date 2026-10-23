import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import * as Sentry from '@sentry/react'
import App from './App'
import { AuthProvider } from '@/auth/AuthProvider'
import { ColdStartBanner } from '@/components/ColdStartBanner'
import './index.css'

const sentryDsn = import.meta.env.VITE_SENTRY_DSN
if (sentryDsn) Sentry.init({ dsn: sentryDsn, environment: import.meta.env.MODE })

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } })

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter><AuthProvider><ColdStartBanner />{sentryDsn ? <Sentry.ErrorBoundary fallback={<div role="alert" className="p-8 text-center">The app encountered an unexpected error. Reload to continue.</div>}><App /></Sentry.ErrorBoundary> : <App />}</AuthProvider></BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
