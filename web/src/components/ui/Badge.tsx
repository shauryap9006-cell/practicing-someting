import React from 'react';
import { cn } from '@/lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'ok' | 'warn' | 'danger' | 'neutral';
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = 'neutral',
  children,
  ...props
}) => {
  const variantClasses = {
    ok: 'badge-ok',
    warn: 'badge-warn',
    danger: 'badge-danger',
    neutral: 'badge-neutral',
  };

  return (
    <span className={cn(variantClasses[variant], className)} {...props}>
      {children}
    </span>
  );
};
