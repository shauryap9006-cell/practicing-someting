import React from 'react';
import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', isLoading = false, children, disabled, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center justify-center font-sans font-medium transition-colors duration-120 select-none disabled:opacity-50 disabled:pointer-events-none rounded-sm focus-visible:outline-none';

    const variants = {
      primary: 'bg-accent text-bg hover:brightness-110 active:brightness-95 font-semibold shadow-none border-0',
      secondary: 'bg-panel-2 text-text-main hover:bg-hairline active:bg-panel border border-hairline',
      outline: 'bg-transparent text-text-main border border-hairline hover:bg-panel-2 hover:border-text-dim/40',
      ghost: 'bg-transparent text-text-dim hover:text-text-main hover:bg-panel-2 border-0',
      danger: 'bg-danger text-bg font-semibold hover:brightness-110 active:brightness-95 border-0',
    };

    const sizes = {
      sm: 'h-7 px-2.5 text-xs gap-1.5',
      md: 'h-8 px-3.5 text-[13px] gap-2',
      lg: 'h-9 px-4 text-sm gap-2',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading && <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
