import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { deleteCampaign, type Campaign } from '@/api/campaigns'
import { ApiError } from '@/api/client'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Button } from '@/components/ui/button'

export function SettingsTab({ campaign }: { campaign: Campaign }) {
  const client = useQueryClient()
  const navigate = useNavigate()
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState('')
  const remove = useMutation({
    mutationFn: () => deleteCampaign(campaign.id),
    onSuccess: async () => {
      client.removeQueries({ queryKey: ['campaign', campaign.id] })
      await client.invalidateQueries({ queryKey: ['campaigns'] })
      navigate('/campaigns')
    },
    onError: (reason) => setError(reason instanceof ApiError ? reason.message : 'Could not delete this campaign. Please retry.'),
  })

  return <div className="max-w-2xl space-y-5">
    <section className="rounded-2xl border border-danger/20 bg-[#090e1b] p-5">
      <h2 className="font-heading text-lg font-semibold">Delete campaign</h2>
      <p className="my-2 text-sm leading-6 text-muted">Permanently delete <strong className="text-foreground">{campaign.name}</strong>, along with its click records. This action cannot be undone.</p>
      {error && <p role="alert" className="mb-3 text-sm text-danger">{error}</p>}
      <Button className="bg-danger text-white hover:bg-red-400" onClick={() => { setError(''); setConfirming(true) }}>Delete campaign</Button>
    </section>
    <ConfirmDialog open={confirming} title={`Delete “${campaign.name}”?`} detail="The campaign and its recorded clicks will be permanently removed." confirmLabel="Delete campaign" busy={remove.isPending} error={error || undefined} onCancel={() => setConfirming(false)} onConfirm={() => remove.mutate()} />
  </div>
}
