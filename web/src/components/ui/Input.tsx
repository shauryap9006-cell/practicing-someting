import React from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = 'text', error, ...props }, ref) => {
    return (
      <div className="w-full">
        <input
          type={type}
          ref={ref}
          className={cn(
            'flex h-8 w-full rounded-sm border bg-panel px-3 py-1 text-[13px] text-text-main shadow-none transition-colors duration-120 placeholder:text-text-dim/60 focus-visible:outline-none focus-visible:border-accent disabled:cursor-not-allowed disabled:opacity-50',
            error ? 'border-danger focus-visible:border-danger' : 'border-hairline',
            className
          )}
          aria-invalid={Boolean(error)}
          {...props}
        />
        {error && <p className="mt-1 text-xs text-danger font-sans">{error}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';
