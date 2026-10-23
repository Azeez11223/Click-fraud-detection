import { useEffect, useState } from 'react'
import { healthCheck } from '@/api/auth'

export function ApiStatusBanner() {
  const [unreachable, setUnreachable] = useState(false)
  useEffect(() => {
    let active = true
    healthCheck().then(() => { if (active) setUnreachable(false) })
      .catch(() => { if (active) setUnreachable(true) })
    return () => { active = false }
  }, [])
  if (!unreachable) return null
  return <div role="status" className="mb-5 flex items-center gap-2 rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-red-200">
    <span aria-hidden="true">●</span> API unavailable. Check that the AdShield backend is running, then try again.
  </div>
}
