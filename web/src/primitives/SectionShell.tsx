import React from 'react';

export interface SectionShellProps {
  microLabel?: string;
  title?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  headerClassName?: string;
  bodyClassName?: string;
}

export const SectionShell: React.FC<SectionShellProps> = ({
  microLabel,
  title,
  action,
  children,
  className = '',
  headerClassName = '',
  bodyClassName = '',
}) => {
  const hasHeader = Boolean(microLabel || title || action);

  return (
    <section
      className={`bg-surface border border-line rounded-[4px] overflow-hidden transition-colors ${className}`}
    >
      {hasHeader && (
        <div
          className={`flex items-center justify-between px-4 py-3 border-b border-line/60 bg-surface ${headerClassName}`}
        >
          <div className="flex flex-col gap-0.5">
            {microLabel && (
              <span className="font-mono text-[10px] uppercase tracking-wider text-muted select-none">
                {microLabel}
              </span>
            )}
            {title && (
              <h3 className="font-serif text-base font-semibold text-ink leading-tight">
                {title}
              </h3>
            )}
          </div>
          {action && <div className="flex items-center gap-2">{action}</div>}
        </div>
      )}
      <div className={`p-4 sm:p-5 ${bodyClassName}`}>{children}</div>
    </section>
  );
};
