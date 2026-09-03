import React from 'react';
import { useLocation } from 'react-router-dom';
import { useTrackModal } from '@/context/TrackModalContext';
import { Radio } from 'lucide-react';

export const PassengerFAB: React.FC = () => {
  const location = useLocation();
  const { openModal, lang } = useTrackModal();

  // E4: On mobile: sticky bottom-right FAB "Track" (only on non-detail pages)
  // Hide on detail pages (/track/:trainNo or /track)
  const isDetailPage = location.pathname.startsWith('/track');
  if (isDetailPage) return null;

  return (
    <div className="sm:hidden fixed bottom-6 right-5 z-40">
      <button
        type="button"
        onClick={() => openModal()}
        className="h-12 px-4 bg-[#F5A524] hover:bg-[#F5A524]/90 text-[#0A0B0D] font-mono font-bold text-xs rounded-full shadow-[0_4px_16px_rgba(245,165,36,0.4)] flex items-center gap-2 transition-transform active:scale-95 min-w-[44px] min-h-[44px]"
        aria-label={lang === 'HI' ? 'ट्रेन ट्रैक करें' : 'Track Train'}
      >
        <Radio className="w-4 h-4 animate-pulse" />
        <span>{lang === 'HI' ? 'ट्रैक करें' : 'Track'}</span>
      </button>
    </div>
  );
};
