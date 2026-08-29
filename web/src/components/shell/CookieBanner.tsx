import React, { useState, useEffect } from 'react';
import { getConsentStatus, setConsentStatus } from '@/lib/analytics';
import { Button } from '@/components/ui/Button';

interface CookieBannerProps {
  forceOpen?: boolean;
  onClose?: () => void;
}

export const CookieBanner: React.FC<CookieBannerProps> = ({ forceOpen = false, onClose }) => {
  const [visible, setVisible] = useState<boolean>(false);

  useEffect(() => {
    const current = getConsentStatus();
    if (current === 'pending' || forceOpen) {
      setVisible(true);
    } else {
      setVisible(false);
    }
  }, [forceOpen]);

  if (!visible) return null;

  const handleAccept = () => {
    setConsentStatus('accepted');
    setVisible(false);
    if (onClose) onClose();
  };

  const handleDecline = () => {
    setConsentStatus('declined');
    setVisible(false);
    if (onClose) onClose();
  };

  return (
    <div className="fixed bottom-10 left-4 z-50 w-full max-w-[360px] bg-panel border border-hairline p-4 shadow-xl text-[13px] animate-in fade-in slide-in-from-bottom-2 duration-150 rounded-none">
      <div className="font-semibold text-text-main text-xs uppercase tracking-wider font-mono mb-1">
        Telemetry & Privacy
      </div>
      <p className="text-text-dim text-xs leading-relaxed mb-3 font-sans">
        We use privacy-friendly, cookieless analytics to understand usage. No ads, no cross-site tracking.
      </p>
      <div className="flex items-center gap-2">
        <Button
          variant="primary"
          size="sm"
          onClick={handleAccept}
          className="flex-1 text-xs"
        >
          Accept
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleDecline}
          className="flex-1 text-xs"
        >
          Decline
        </Button>
      </div>
    </div>
  );
};
