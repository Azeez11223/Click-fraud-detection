import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

const buttonStyles = cva('inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:pointer-events-none disabled:opacity-50', {
  variants: {
    variant: {
      default: 'bg-accent text-slate-950 hover:bg-blue-300',
      outline: 'border border-border bg-transparent text-foreground hover:bg-white/5',
      ghost: 'text-muted hover:bg-white/5 hover:text-foreground',
    },
    size: { default: 'h-11 px-4', sm: 'h-9 px-3', icon: 'h-10 w-10' },
  },
  defaultVariants: { variant: 'default', size: 'default' },
})

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonStyles> {
  asChild?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button({ className, variant, size, asChild = false, ...props }, ref) {
  const Component = asChild ? Slot : 'button'
  return <Component ref={ref} className={cn(buttonStyles({ variant, size }), className)} {...props} />
})
