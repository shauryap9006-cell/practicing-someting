import React from 'react';

interface EmptyStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  onLoadDemo?: () => void;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No active telemetry data',
  description = 'No signals detected in the selected block section or time window.',
  onRetry,
  onLoadDemo,
  actionLabel,
  onAction,
  className = '',
}) => {
  return (
    <div
      className={`p-10 text-center bg-[#101216] border border-[#23272F] rounded-lg flex flex-col items-center justify-center font-mono select-none ${className}`}
    >
      {/* Signal Blue Line Illustration */}
      <div className="w-16 h-16 mb-4 relative flex items-center justify-center">
        <div className="absolute inset-0 rounded-full border border-[#6C9FFF]/20 bg-[rgba(108,159,255,0.06)] animate-pulse" />
        <svg
          className="w-8 h-8 text-[#6C9FFF]"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3 12h3l3-6 4 12 3-6h5"
          />
        </svg>
      </div>

      <h3 className="text-sm font-bold text-[#E9EBEE] uppercase tracking-wider mb-1">
        {title}
      </h3>
      <p className="text-xs text-[#A3ABB6] font-sans max-w-md mb-6 leading-relaxed">
        {description}
      </p>

      {/* Action Buttons */}
      <div className="flex items-center gap-3">
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="px-3.5 py-1.5 bg-[#15181D] hover:bg-[#1B1F26] border border-[#23272F] hover:border-[#2E333D] text-[#E9EBEE] text-xs font-semibold rounded-sm transition-colors"
          >
            Retry Query
          </button>
        )}

        {onLoadDemo && (
          <button
            type="button"
            onClick={onLoadDemo}
            className="px-3.5 py-1.5 bg-[#F5A524] hover:bg-[#F5A524]/90 text-[#0A0B0D] text-xs font-bold rounded-sm transition-colors shadow-sm"
          >
            Load Demo Telemetry
          </button>
        )}

        {actionLabel && onAction && (
          <button
            type="button"
            onClick={onAction}
            className="px-3.5 py-1.5 bg-[#6C9FFF] hover:bg-[#6C9FFF]/90 text-[#0A0B0D] text-xs font-bold rounded-sm transition-colors"
          >
            {actionLabel}
          </button>
        )}
      </div>
    </div>
  );
};
