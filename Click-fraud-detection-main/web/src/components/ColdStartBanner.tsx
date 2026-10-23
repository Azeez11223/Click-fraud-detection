import { useEffect, useState } from 'react'
import { healthCheck } from '@/api/auth'
import { Button } from '@/components/ui/button'

type ColdStartState='waking'|'unreachable'|null
export function ColdStartBanner(){const [state,setState]=useState<ColdStartState>(null);const [retrying,setRetrying]=useState(false);const [message,setMessage]=useState('')
 useEffect(()=>{const receive=(event:Event)=>{const detail=(event as CustomEvent<'waking'|'ready'|'unreachable'>).detail;if(detail==='ready'){setState(null);setMessage('')}else{setState(detail);setMessage('')}};window.addEventListener('adshield:cold-start',receive);return()=>window.removeEventListener('adshield:cold-start',receive)},[])
 if(!state)return null
 async function retry(){setRetrying(true);setMessage('');try{await healthCheck();setState(null)}catch{setState('unreachable');setMessage('The server is still unavailable. Try again shortly.')}finally{setRetrying(false)}}
 return <div role="status" aria-live="polite" className="fixed inset-x-4 top-3 z-[100] mx-auto flex max-w-2xl items-center justify-between gap-4 rounded-xl border border-warning/40 bg-[#171506] px-4 py-3 text-sm shadow-xl"><span><strong className="text-warning">{state==='waking'?'Waking up the server':'The server is taking longer than expected'}</strong>{message&&<span className="ml-2 text-foreground">{message}</span>}</span><Button size="sm" variant="outline" disabled={retrying} onClick={()=>void retry()}>{retrying?'Retrying…':'Retry'}</Button></div>
}
