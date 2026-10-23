import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { ApiError } from '@/api/client'
import { createCampaign, type CampaignInput } from '@/api/campaigns'
import { Button } from '@/components/ui/button'

const requiredNumber = (min: number, max: number, message: string) => z.preprocess(
  (value) => value === '' ? undefined : value,
  z.coerce.number().min(min, message).max(max, message),
)

const campaignSchema = z.object({
  name: z.string().trim().min(1, 'Campaign name is required').max(200, 'Name must be 200 characters or fewer'),
  ad_type: z.enum(['Display', 'Video', 'Search', 'Social']),
  platform: z.enum(['Google', 'Facebook', 'Instagram']),
  purpose: z.enum(['Traffic', 'Sales', 'Awareness']),
  cpc: requiredNumber(0, 100000, 'CPC must be between 0 and $100,000'),
  avg_conversion_value: requiredNumber(0, 10000000, 'Value must be between 0 and $10,000,000'),
  expected_conversion_rate: requiredNumber(0, 1, 'Rate must be between 0 and 1'),
})

export function CampaignForm({ onCreated, onCancel }: { onCreated: (id: number) => void; onCancel: () => void }) {
  const [serverError, setServerError] = useState('')
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<z.input<typeof campaignSchema>, unknown, CampaignInput>({
    resolver: zodResolver(campaignSchema),
    defaultValues: { name: '', ad_type: 'Search', platform: 'Google', purpose: 'Traffic', cpc: 0.5, avg_conversion_value: 25, expected_conversion_rate: 0.02 },
  })

  async function submit(values: CampaignInput) {
    setServerError('')
    try { const result = await createCampaign(values); onCreated(result.campaign_id) }
    catch (error) { setServerError(error instanceof ApiError ? error.message : 'Could not create the campaign.') }
  }

  return <form className="space-y-4" noValidate onSubmit={handleSubmit(submit)}>
    <FormField label="Campaign name" error={errors.name?.message}><input className="campaign-input" placeholder="e.g. Summer Sale Ads" {...register('name')} /></FormField>
    <div className="grid gap-4 sm:grid-cols-2">
      <FormField label="Ad type" error={errors.ad_type?.message}><select className="campaign-input" {...register('ad_type')}><option>Display</option><option>Video</option><option>Search</option><option>Social</option></select></FormField>
      <FormField label="Platform" error={errors.platform?.message}><select className="campaign-input" {...register('platform')}><option>Google</option><option>Facebook</option><option>Instagram</option></select></FormField>
      <FormField label="Purpose" error={errors.purpose?.message}><select className="campaign-input" {...register('purpose')}><option>Traffic</option><option>Sales</option><option>Awareness</option></select></FormField>
      <FormField label="Cost per click ($)" error={errors.cpc?.message}><input className="campaign-input font-mono" type="number" min="0" step="0.01" {...register('cpc')} /></FormField>
      <FormField label="Average conversion value ($)" error={errors.avg_conversion_value?.message}><input className="campaign-input font-mono" type="number" min="0" step="0.01" {...register('avg_conversion_value')} /></FormField>
      <FormField label="Expected conversion rate (0–1)" error={errors.expected_conversion_rate?.message}><input className="campaign-input font-mono" type="number" min="0" max="1" step="0.001" {...register('expected_conversion_rate')} /></FormField>
    </div>
    {serverError && <p role="alert" className="text-sm text-danger">{serverError}</p>}
    <div className="flex justify-end gap-3 border-t border-border pt-4"><Button variant="outline" type="button" onClick={onCancel} disabled={isSubmitting}>Cancel</Button><Button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Creating…' : 'Create campaign'}</Button></div>
  </form>
}

function FormField({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return <label className="block space-y-2 text-xs font-medium text-slate-300">{label}{children}{error && <span className="block text-xs text-danger">{error}</span>}</label>
}
