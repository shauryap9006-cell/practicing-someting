import React from 'react';

export interface ErrorStateProps {
  title?: string;
  message: string;
  details?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Service Anomaly / Connection Fault',
  message,
  details,
  onRetry,
  className = '',
}) => {
  return (
    <div
      className={`border border-restrict/40 bg-surface rounded-[4px] p-5 flex flex-col gap-3 ${className}`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <div className="w-3 h-3 rounded-[2px] bg-restrict mt-1 shrink-0" />
        <div className="flex flex-col gap-1">
          <h4 className="font-serif text-base font-semibold text-ink leading-tight">
            {title}
          </h4>
          <p className="font-sans text-xs sm:text-sm text-ink/80 leading-relaxed">
            {message}
          </p>
        </div>
      </div>

      {details && (
        <pre className="p-3 bg-raised border border-line rounded-[3px] font-mono text-[11px] text-muted overflow-x-auto whitespace-pre-wrap">
          {details}
        </pre>
      )}

      {onRetry && (
        <div className="pt-2 flex justify-end">
          <button
            type="button"
            onClick={onRetry}
            className="font-mono text-xs px-3.5 py-1.5 rounded-[4px] border border-ink bg-surface text-ink hover:bg-raised transition-colors cursor-pointer select-none font-medium"
          >
            RETRY TRANSMISSION ↺
          </button>
        </div>
      )}
    </div>
  );
};
