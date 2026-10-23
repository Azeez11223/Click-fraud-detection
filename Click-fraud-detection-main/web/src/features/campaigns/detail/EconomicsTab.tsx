import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { updateCampaignEconomics, getThresholdAnalysis, updateCampaignThreshold, type Campaign } from '@/api/campaigns'
import { ApiError } from '@/api/client'
import { LoadingSkeleton, QueryError } from '@/components/DataState'
import { Button } from '@/components/ui/button'

const requiredNumber = (min: number, max: number) => z.preprocess(
  (value) => value === '' ? undefined : value,
  z.coerce.number().min(min).max(max),
)
const economicsSchema = z.object({
  cpc: requiredNumber(0, 100000),
  avg_conversion_value: requiredNumber(0, 10000000),
  expected_conversion_rate: requiredNumber(0, 1),
})
type EconomicsValues = z.infer<typeof economicsSchema>

export function EconomicsTab({ campaign }: { campaign: Campaign }) {
  const client = useQueryClient()
  const id = campaign.id
  const [preview, setPreview] = useState<number | null>(null)
  const [formError, setFormError] = useState('')
  const [thresholdError, setThresholdError] = useState('')
  const { register, handleSubmit, reset, formState: { errors } } = useForm<z.input<typeof economicsSchema>, unknown, EconomicsValues>({ resolver: zodResolver(economicsSchema), defaultValues: formValues(campaign) })
  const analysis = useQuery({ queryKey: ['campaign-threshold', id, preview], queryFn: () => getThresholdAnalysis(id, preview ?? undefined), enabled: true, refetchOnWindowFocus: true })

  useEffect(() => { reset(formValues(campaign)) }, [campaign, reset])
  useEffect(() => { if (preview === null && analysis.isSuccess) setPreview(analysis.data.active_block_threshold) }, [analysis.data, analysis.isSuccess, preview])

  const costs = useMutation({
    mutationFn: (values: EconomicsValues) => updateCampaignEconomics(id, values),
    onSuccess: (_result, values) => {
      client.setQueryData<Campaign>(['campaign', id], (current) => current ? { ...current, ...values } : current)
      void client.invalidateQueries({ queryKey: ['campaign-threshold', id] })
      setFormError('')
    },
    onError: (error) => setFormError(apiMessage(error, 'Could not save cost assumptions.')),
  })
  const blockThreshold = useMutation({
    mutationFn: (value: number) => updateCampaignThreshold(id, value),
    onSuccess: (_result, value) => {
      client.setQueryData<Campaign>(['campaign', id], (current) => current ? { ...current, block_threshold: value } : current)
      void client.invalidateQueries({ queryKey: ['campaign-threshold', id] })
      setThresholdError('')
    },
    onError: (error) => setThresholdError(apiMessage(error, 'Could not save the block threshold.')),
  })

  async function saveCosts(values: EconomicsValues) { await costs.mutateAsync(values) }
  const selected = Math.min(1, Math.max(0.01, preview ?? analysis.data?.active_block_threshold ?? 0.5))
  return <div className="space-y-5">
    <section className="rounded-2xl border border-border bg-[#090e1b] p-5">
      <h2 className="font-heading text-lg font-semibold">Campaign cost assumptions</h2><p className="mb-5 mt-1 text-sm text-muted">These values shape the recommended fraud blocking threshold.</p>
      <form className="grid gap-4 sm:grid-cols-3" noValidate onSubmit={handleSubmit(saveCosts)}>
        <Field label="Cost per click ($)" error={errors.cpc?.message}><input className="campaign-input font-mono" type="number" min="0" step="0.01" {...register('cpc')} /></Field>
        <Field label="Average conversion value ($)" error={errors.avg_conversion_value?.message}><input className="campaign-input font-mono" type="number" min="0" step="0.01" {...register('avg_conversion_value')} /></Field>
        <Field label="Expected conversion rate (0–1)" error={errors.expected_conversion_rate?.message}><input className="campaign-input font-mono" type="number" min="0" max="1" step="0.001" {...register('expected_conversion_rate')} /></Field>
        {formError && <p role="alert" className="sm:col-span-3 text-sm text-danger">{formError}</p>}
        <div className="sm:col-span-3"><Button disabled={costs.isPending}>{costs.isPending ? 'Saving assumptions…' : 'Save cost assumptions'}</Button></div>
      </form>
    </section>
    {analysis.isPending ? <div className="rounded-2xl border border-border bg-[#090e1b] p-5"><LoadingSkeleton rows={4} /></div>
      : analysis.isError ? <QueryError error={analysis.error} retry={() => void analysis.refetch()} /> : <section className="rounded-2xl border border-border bg-[#090e1b] p-5">
        <div className="mb-5"><h2 className="font-heading text-lg font-semibold">Economics & threshold</h2><p className="mt-1 text-sm text-muted">Recommended: <span className="font-mono text-foreground">{analysis.data.recommended_block_threshold.toFixed(2)}</span> · Active: <span className="font-mono text-foreground">{analysis.data.active_block_threshold.toFixed(2)}</span></p></div>
        <label className="block max-w-2xl text-sm font-medium">Preview block sensitivity <span className="ml-2 font-mono text-accent">{selected.toFixed(2)}</span>
          <input className="mt-4 w-full accent-accent" aria-label="Preview block sensitivity" type="range" min="0.01" max="1" step="0.01" value={selected} onChange={(event) => setPreview(Number(event.target.value))} />
          <span className="mt-1 flex justify-between font-mono text-xs text-muted"><span>0.01 · More blocking</span><span>1.00 · Less blocking</span></span>
        </label>
        {thresholdError && <p role="alert" className="mt-3 text-sm text-danger">{thresholdError}</p>}
        <div className="mt-5"><Button disabled={blockThreshold.isPending || Math.abs(selected - analysis.data.active_block_threshold) < 0.005} onClick={() => blockThreshold.mutate(selected)}>{blockThreshold.isPending ? 'Saving threshold…' : 'Save block threshold'}</Button></div>
        <div className="mt-6 grid gap-3 sm:grid-cols-3"><Estimate label="Estimated wasted spend saved" value={`$${analysis.data.analysis.estimated_wasted_spend_saved.toFixed(2)}`} /><Estimate label="Estimated legitimate conversions lost" value={analysis.data.analysis.estimated_legitimate_conversions_lost.toFixed(2)} /><Estimate label="Estimated conversion value lost" value={`$${analysis.data.analysis.estimated_conversion_value_lost.toFixed(2)}`} /></div>
        <p className="mt-5 rounded-lg border border-warning/20 bg-warning/[0.04] p-3 text-xs leading-5 text-muted">{analysis.data.estimate_notice}</p>
      </section>}
  </div>
}

function formValues(campaign: Campaign): EconomicsValues { return { cpc: campaign.cpc ?? 0.5, avg_conversion_value: campaign.avg_conversion_value ?? 25, expected_conversion_rate: campaign.expected_conversion_rate ?? 0.02 } }
function apiMessage(error: unknown, fallback: string) { return error instanceof ApiError ? error.message : fallback }
function Estimate({ label, value }: { label: string; value: string }) { return <div className="rounded-xl border border-border bg-background/60 p-4"><p className="text-xs leading-5 text-muted">{label}</p><p className="mt-2 font-mono text-lg font-semibold">{value}</p></div> }
function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) { return <label className="block space-y-2 text-xs font-medium text-slate-300">{label}{children}{error && <span className="block text-danger">{error}</span>}</label> }
