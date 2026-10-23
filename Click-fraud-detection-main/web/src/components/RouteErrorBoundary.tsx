import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'

interface Props { children: ReactNode }
interface State { failed: boolean }

export class RouteErrorBoundary extends Component<Props, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State { return { failed: true } }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error('Route rendering failed', error, info.componentStack) }

  render() {
    if (!this.state.failed) return this.props.children
    return <div className="grid min-h-[60vh] place-items-center p-8 text-center">
      <div><h1 className="font-heading text-2xl font-bold">This page ran into a problem</h1>
        <p className="my-3 text-sm text-muted">Try returning to the dashboard.</p>
        <Button asChild><Link to="/dashboard">Back to dashboard</Link></Button></div>
    </div>
  }
}
