import { Button } from '@/components/ui/button'
import { useEffect, useRef } from 'react'

export function ConfirmDialog({ open, title, detail, confirmLabel, busy = false, error, onConfirm, onCancel }: {
  open: boolean
  title: string
  detail: string
  confirmLabel: string
  busy?: boolean
  error?: string
  onConfirm: () => void
  onCancel: () => void
}) {
  const cancelButton = useRef<HTMLButtonElement>(null)
  const dialog = useRef<HTMLElement>(null)
  useEffect(() => {
    if (!open) return
    cancelButton.current?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busy) onCancel()
      if (event.key === 'Tab') {
        const controls = dialog.current?.querySelectorAll<HTMLElement>('button:not([disabled])')
        if (!controls?.length) return
        const first = controls[0]
        const last = controls[controls.length - 1]
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, busy, onCancel])
  if (!open) return null
  return <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4">
    <section ref={dialog} role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-detail" className="w-full max-w-md rounded-2xl border border-border bg-[#0a0f1d] p-6 shadow-2xl">
      <h2 id="confirm-title" className="font-heading text-xl font-bold">{title}</h2>
      <p id="confirm-detail" className="my-3 text-sm leading-6 text-muted">{detail}</p>
      {error && <p role="alert" className="mb-3 text-sm text-danger">{error}</p>}
      <div className="mt-5 flex justify-end gap-3"><Button ref={cancelButton} variant="outline" onClick={onCancel} disabled={busy}>Cancel</Button>
        <Button className="bg-danger text-white hover:bg-red-400" onClick={onConfirm} disabled={busy}>{busy ? 'Working…' : confirmLabel}</Button></div>
    </section>
  </div>
}
