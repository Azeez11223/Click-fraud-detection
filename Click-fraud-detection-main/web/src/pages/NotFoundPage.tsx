import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'

export default function NotFoundPage() {
  return <div className="grid min-h-[70vh] place-items-center p-8 text-center">
    <div><p className="font-mono text-sm text-accent">404</p><h1 className="mt-3 font-heading text-3xl font-bold">Page not found</h1>
      <p className="my-3 text-sm text-muted">The address may be incorrect or the page may have moved.</p>
      <Button asChild><Link to="/dashboard">Go to dashboard</Link></Button></div>
  </div>
}
