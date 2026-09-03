import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTrackModal } from '@/context/TrackModalContext';
import { api, PassengerSearchResult, PassengerPopularTrain } from '@/lib/api';
import { AspectLamp, AspectType } from '@/components/aspect';
import {
  Search,
  X,
  Clock,
  Flame,
  ArrowRight,
  AlertCircle,
  WifiOff,
  ChevronRight,
  Sparkles,
  Ticket,
  Train,
} from 'lucide-react';

interface RecentSearchItem {
  id: string; // train_no or masked PNR
  query: string;
  name: string;
  type: 'TRAIN' | 'PNR';
  route?: string;
  pnrRaw?: string;
  lamp?: 'green' | 'amber' | 'red' | 'blue';
}

const STORAGE_KEY_RECENTS = 'railtwin_recent_searches_v1';

export const TrackTrainModal: React.FC = () => {
  const { isOpen, closeModal, initialInput, lang } = useTrackModal();
  const navigate = useNavigate();

  const [inputVal, setInputVal] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [pnrLookupLoading, setPnrLookupLoading] = useState(false);
  const [pnrError, setPnrError] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [isOffline, setIsOffline] = useState(!navigator.onLine);

  const inputRef = useRef<HTMLInputElement>(null);
  const modalContainerRef = useRef<HTMLDivElement>(null);

  // Monitor network online/offline state
  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Recent Searches from localStorage (Zero hardcoded data)
  const [recents, setRecents] = useState<RecentSearchItem[]>(() => {
    if (typeof window === 'undefined') return [];
    try {
      const stored = localStorage.getItem(STORAGE_KEY_RECENTS);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const saveRecent = useCallback((item: RecentSearchItem) => {
    setRecents((prev) => {
      const filtered = prev.filter((r) => r.id !== item.id);
      const next = [item, ...filtered].slice(0, 4);
      try {
        localStorage.setItem(STORAGE_KEY_RECENTS, JSON.stringify(next));
      } catch {}
      return next;
    });
  }, []);

  const removeRecent = useCallback((id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setRecents((prev) => {
      const next = prev.filter((r) => r.id !== id);
      try {
        localStorage.setItem(STORAGE_KEY_RECENTS, JSON.stringify(next));
      } catch {}
      return next;
    });
  }, []);

  // Rotating Hint every 4 seconds (M1)
  const placeholdersEN = ['Train number, name, or PNR…', 'Try 12003', 'Or your 10-digit PNR'];
  const placeholdersHI = ['ट्रेन नंबर, नाम या PNR…', 'उदा. 12003', 'या अपना 10-अंकीय PNR'];

  useEffect(() => {
    if (!isOpen) return;
    const interval = setInterval(() => {
      setPlaceholderIndex((prev) => (prev + 1) % placeholdersEN.length);
    }, 4000);
    return () => clearInterval(interval);
  }, [isOpen]);

  // Sync initial input and focus when modal opens (M1 / A1: < 100ms)
  useEffect(() => {
    if (isOpen) {
      setInputVal(initialInput || '');
      setDebouncedQuery(initialInput || '');
      setValidationError(null);
      setPnrError(null);
      setSelectedIndex(0);

      // Focus input within 50ms
      const timer = setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
          inputRef.current.select();
        }
      }, 30);
      return () => clearTimeout(timer);
    }
  }, [isOpen, initialInput]);

  // Smart Input Mode detection (M2)
  // User types 10 digits -> PNR
  // User types 4 or 5 digits -> Train No
  // User types letters / mixed (>=2 chars) -> Name
  const trimmed = inputVal.trim();
  const isAllDigits = /^\d+$/.test(trimmed);

  const detectedMode = useMemo<'PNR' | 'TRAIN_NO' | 'TRAIN_NAME' | null>(() => {
    if (!trimmed) return null;
    if (isAllDigits) {
      if (trimmed.length === 10) return 'PNR';
      if (trimmed.length >= 4 && trimmed.length <= 5) return 'TRAIN_NO';
      return null;
    }
    if (trimmed.length >= 2) return 'TRAIN_NAME';
    return null;
  }, [trimmed, isAllDigits]);

  // Pre-API Client Validation (M2)
  useEffect(() => {
    if (!trimmed) {
      setValidationError(null);
      return;
    }
    if (isAllDigits) {
      if (trimmed.length > 5 && trimmed.length < 10) {
        setValidationError(
          lang === 'HI'
            ? `PNR 10 अंकों का होता है (${trimmed.length}/10 अंक दर्ज)`
            : `PNR is 10 digits (${trimmed.length}/10 entered)`
        );
        return;
      }
      if (trimmed.length > 10) {
        setValidationError(lang === 'HI' ? 'PNR 10 अंकों से अधिक नहीं हो सकता' : 'PNR cannot exceed 10 digits');
        return;
      }
      if (trimmed.length < 4) {
        setValidationError(lang === 'HI' ? 'ट्रेन नंबर 4 या 5 अंकों का होता है' : 'Train number must be 4 or 5 digits');
        return;
      }
    } else {
      if (trimmed.length < 2) {
        setValidationError(lang === 'HI' ? 'नाम से खोजने के लिए कम से कम 2 अक्षर लिखें' : 'Type at least 2 characters to search by name');
        return;
      }
    }
    setValidationError(null);
  }, [trimmed, isAllDigits, lang]);

  // Debounce 250ms for live suggestions (M2 / M3)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(trimmed);
      setSelectedIndex(0);
    }, 250);
    return () => clearTimeout(timer);
  }, [trimmed]);

  // Live Suggestions Query (M3 - GET /v1/passenger/search?q=...)
  const isSearchQueryActive = !validationError && debouncedQuery.length >= 2 && !isOffline;

  const {
    data: searchResults,
    isLoading: isSearchLoading,
    isError: isSearchError,
    refetch: refetchSearch,
  } = useQuery({
    queryKey: ['passenger-search', debouncedQuery],
    queryFn: () => api.searchPassengerTrains(debouncedQuery),
    enabled: isSearchQueryActive,
    staleTime: 30000,
  });

  // Popular Trains Query (M4 - GET /v1/passenger/popular)
  // If popular API fails -> gracefully hide group entirely (no static fallback)
  const {
    data: popularTrains,
    isLoading: isPopularLoading,
  } = useQuery({
    queryKey: ['passenger-popular'],
    queryFn: () => api.getPopularPassengerTrains(),
    enabled: isOpen && !trimmed,
    staleTime: 60000,
  });

  // PNR Resolution Handler (M5)
  const handlePnrDirect = async (pnrNum: string) => {
    setPnrLookupLoading(true);
    setPnrError(null);
    try {
      const pnrData = await api.getPassengerPNR(pnrNum);
      if (pnrData && pnrData.status in { valid: 1, completed: 1 }) {
        saveRecent({
          id: `••••••${pnrNum.slice(-4)}`,
          query: pnrNum,
          name: pnrData.train_name,
          type: 'PNR',
          route: `${pnrData.boarding.code} → ${pnrData.destination.code}`,
          pnrRaw: pnrNum,
          lamp: 'amber',
        });
        closeModal();
        navigate(`/track/${pnrData.train_no}?stop=${pnrData.boarding.code}&pnr=${pnrNum}`);
      } else {
        setPnrError(
          lang === 'HI'
            ? 'यह PNR नहीं मिला। कृपया नंबर जांचें या ट्रेन के नाम से ट्रैक करें →'
            : "We couldn't find this PNR. Check the number or track by train name instead →"
        );
      }
    } catch (err: any) {
      setPnrError(
        lang === 'HI'
          ? 'यह PNR नहीं मिला। कृपया नंबर जांचें या ट्रेन के नाम से ट्रैक करें →'
          : "We couldn't find this PNR. Check the number or track by train name instead →"
      );
    } finally {
      setPnrLookupLoading(false);
    }
  };

  // Select a suggestion row
  const handleSelectTrain = (t: PassengerSearchResult | PassengerPopularTrain) => {
    saveRecent({
      id: t.train_no,
      query: t.train_no,
      name: t.name,
      type: 'TRAIN',
      route: t.route_short,
      lamp: t.status_lamp,
    });
    closeModal();
    navigate(`/track/${t.train_no}`);
  };

  // Keyboard navigation: ↑/↓ and Enter and Escape (A1, A9)
  const currentList = useMemo(() => {
    if (searchResults && searchResults.length > 0) return searchResults;
    return [];
  }, [searchResults]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === 'Escape') {
        e.preventDefault();
        closeModal();
        return;
      }

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (currentList.length > 0 ? (prev + 1) % currentList.length : 0));
        return;
      }

      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (currentList.length > 0 ? (prev - 1 + currentList.length) % currentList.length : 0));
        return;
      }

      if (e.key === 'Enter') {
        e.preventDefault();
        // If PNR 10 digits, resolve directly
        if (detectedMode === 'PNR') {
          handlePnrDirect(trimmed);
          return;
        }
        if (currentList.length > 0 && currentList[selectedIndex]) {
          handleSelectTrain(currentList[selectedIndex]);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, currentList, selectedIndex, detectedMode, trimmed]);

  // Focus trap inside modal
  useEffect(() => {
    if (!isOpen) return;
    const trapFocus = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;
      const modal = modalContainerRef.current;
      if (!modal) return;

      const focusables = modal.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusables.length === 0) return;

      const first = focusables[0];
      const last = focusables[focusables.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        last.focus();
        e.preventDefault();
      } else if (!e.shiftKey && document.activeElement === last) {
        first.focus();
        e.preventDefault();
      }
    };

    window.addEventListener('keydown', trapFocus);
    return () => window.removeEventListener('keydown', trapFocus);
  }, [isOpen]);

  if (!isOpen) return null;

  // Helper for highlighting matched substring in accent amber
  const highlightMatch = (text: string, query: string) => {
    if (!query || query.length < 2) return text;
    const parts = text.split(new RegExp(`(${query})`, 'gi'));
    return parts.map((part, idx) =>
      part.toLowerCase() === query.toLowerCase() ? (
        <span key={idx} className="text-[#F5A524] font-bold bg-[#F5A524]/10 rounded px-0.5">
          {part}
        </span>
      ) : (
        part
      )
    );
  };

  const currentPlaceholder = lang === 'HI' ? placeholdersHI[placeholderIndex] : placeholdersEN[placeholderIndex];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={lang === 'HI' ? 'ट्रेन या PNR खोजें' : 'Search Train or PNR'}
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 transition-opacity duration-200"
    >
      {/* Backdrop with 4px blur on #0A0B0D/80% */}
      <div
        onClick={closeModal}
        className="fixed inset-0 bg-[#0A0B0D]/80 backdrop-blur-[4px] transition-opacity"
      />

      {/* Modal / Bottom Sheet Container (M1) */}
      <div
        ref={modalContainerRef}
        className="relative z-10 w-full sm:max-w-[560px] bg-[#101216] border border-[#23272F] sm:rounded-lg rounded-t-2xl shadow-2xl flex flex-col max-h-[85vh] sm:max-h-[640px] overflow-hidden animate-in fade-in zoom-in-95 sm:zoom-in-95 duration-200"
      >
        {/* Mobile Drag Handle */}
        <div className="sm:hidden flex justify-center pt-3 pb-1">
          <div className="w-10 h-1 rounded-full bg-[#23272F]" />
        </div>

        {/* Header & Search Input Box */}
        <div className="p-4 border-b border-[#23272F]">
          <div className="relative flex items-center">
            <Search className="absolute left-3.5 w-4 h-4 text-[#A3ABB6] pointer-events-none" />
            <input
              ref={inputRef}
              type="text"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              placeholder={currentPlaceholder}
              autoComplete="off"
              spellCheck="false"
              className="w-full pl-10 pr-28 py-3 bg-[#0A0B0D] border border-[#23272F] focus:border-[#F5A524] rounded-md text-sm text-[#E9EBEE] placeholder-[#6B7480] focus:outline-none transition-colors duration-120 font-sans"
            />

            {/* Smart Mode Detection Badge (M2) */}
            <div className="absolute right-10 flex items-center gap-1 pointer-events-none">
              {detectedMode === 'PNR' && (
                <span className="px-2 py-0.5 bg-[#F5A524]/20 border border-[#F5A524]/50 text-[#F5A524] text-[10px] font-mono font-bold rounded">
                  [PNR]
                </span>
              )}
              {detectedMode === 'TRAIN_NO' && (
                <span className="px-2 py-0.5 bg-[#3DDC97]/20 border border-[#3DDC97]/50 text-[#3DDC97] text-[10px] font-mono font-bold rounded">
                  [TRAIN NO]
                </span>
              )}
              {detectedMode === 'TRAIN_NAME' && (
                <span className="px-2 py-0.5 bg-[#6C9FFF]/20 border border-[#6C9FFF]/50 text-[#6C9FFF] text-[10px] font-mono font-bold rounded">
                  [TRAIN NAME]
                </span>
              )}
            </div>

            {/* Clear / Close Button (min 44px touch target) */}
            {inputVal ? (
              <button
                type="button"
                onClick={() => {
                  setInputVal('');
                  inputRef.current?.focus();
                }}
                className="absolute right-2 p-2 text-[#A3ABB6] hover:text-[#E9EBEE] min-w-[44px] min-h-[44px] flex items-center justify-center transition-colors"
                aria-label="Clear input"
              >
                <X className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={closeModal}
                className="absolute right-2 p-2 text-[#A3ABB6] hover:text-[#E9EBEE] min-w-[44px] min-h-[44px] flex items-center justify-center transition-colors"
                aria-label="Close modal"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Inline Validation Help (M2) */}
          {validationError && (
            <div className="mt-2 text-xs font-mono text-[#F5A524] flex items-center gap-1.5 animate-in fade-in duration-120">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{validationError}</span>
            </div>
          )}

          {/* PNR Error Message (M5) */}
          {pnrError && (
            <div className="mt-2 p-2.5 bg-[#F4506A]/10 border border-[#F4506A]/30 rounded text-xs text-[#F4506A] flex flex-col gap-1">
              <div className="flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                <span>{pnrError}</span>
              </div>
            </div>
          )}

          {/* Offline Banner (M3) */}
          {isOffline && (
            <div className="mt-2 p-2 bg-[#1B1F26] border border-[#23272F] rounded text-xs font-mono text-[#F5A524] flex items-center gap-2">
              <WifiOff className="w-3.5 h-3.5 shrink-0" />
              <span>
                {lang === 'HI'
                  ? 'आप ऑफ़लाइन हैं — केवल हाल की खोजें दिखाई जा रही हैं।'
                  : "You're offline — showing recent searches only."}
              </span>
            </div>
          )}
        </div>

        {/* Modal Body / Results Content */}
        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          {/* STATE 1: PNR Direct Action Button when 10 digits entered */}
          {detectedMode === 'PNR' && !validationError && (
            <div className="p-3 bg-[#15181D] border border-[#F5A524]/30 rounded-md flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded bg-[#F5A524]/10 border border-[#F5A524]/30 flex items-center justify-center text-[#F5A524]">
                  <Ticket className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-mono font-bold text-[#E9EBEE]">PNR {trimmed}</div>
                  <div className="text-[11px] text-[#A3ABB6]">
                    {lang === 'HI' ? 'सीधे यात्रा विवरण और स्टेशन ट्रैक करें' : 'Track booking & expected arrival directly'}
                  </div>
                </div>
              </div>
              <button
                type="button"
                disabled={pnrLookupLoading}
                onClick={() => handlePnrDirect(trimmed)}
                className="px-4 py-2 bg-[#F5A524] hover:bg-[#F5A524]/90 text-[#0A0B0D] font-mono font-bold text-xs rounded transition-colors flex items-center gap-1.5 min-h-[44px]"
              >
                {pnrLookupLoading ? (
                  <span className="animate-spin w-3.5 h-3.5 border-2 border-[#0A0B0D] border-t-transparent rounded-full" />
                ) : (
                  <>
                    <span>{lang === 'HI' ? 'ट्रैक करें' : 'Track PNR'}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </div>
          )}

          {/* STATE 2: In-Flight Search Results */}
          {isSearchLoading && (
            <div className="space-y-2 py-2">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-[56px] rounded-md bg-[#15181D] animate-pulse border border-[#23272F] flex items-center px-4 justify-between"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-[#23272F]" />
                    <div className="space-y-1.5">
                      <div className="w-32 h-3.5 bg-[#23272F] rounded" />
                      <div className="w-48 h-2.5 bg-[#23272F] rounded" />
                    </div>
                  </div>
                  <div className="w-20 h-3 bg-[#23272F] rounded" />
                </div>
              ))}
            </div>
          )}

          {/* STATE 3: Search Error State */}
          {isSearchError && !isOffline && (
            <div className="py-8 text-center space-y-2">
              <p className="text-xs font-mono text-[#F4506A]">
                {lang === 'HI' ? 'खोज सेवा अनुपलब्ध है — ' : 'Search is unavailable — '}
                <button
                  type="button"
                  onClick={() => refetchSearch()}
                  className="underline hover:text-[#E9EBEE] ml-1 font-bold min-h-[44px] inline-flex items-center"
                >
                  {lang === 'HI' ? 'पुनः प्रयास करें' : 'Retry'}
                </button>
              </p>
            </div>
          )}

          {/* STATE 4: Empty Search Results */}
          {trimmed && !isSearchLoading && !isSearchError && searchResults && searchResults.length === 0 && (
            <div className="py-8 text-center space-y-2.5">
              <div className="text-sm text-[#E9EBEE]">
                {lang === 'HI' ? `कोई ट्रेन '${trimmed}' से मेल नहीं खाई` : `No trains matched '${trimmed}'`}
              </div>
              <div className="text-xs text-[#A3ABB6]">
                {lang === 'HI' ? 'नंबर जांचें, या ट्रेन का नाम लिखकर देखें' : 'Check the number, or try the name'}
              </div>
              <button
                type="button"
                onClick={() => {
                  setInputVal('');
                  inputRef.current?.focus();
                }}
                className="text-xs font-mono text-[#F5A524] hover:underline pt-1 inline-flex items-center gap-1 min-h-[44px]"
              >
                <span>{lang === 'HI' ? 'PNR द्वारा खोजें →' : 'Search by PNR instead →'}</span>
              </button>
            </div>
          )}

          {/* STATE 5: Active Suggestions Rows (M3) */}
          {searchResults && searchResults.length > 0 && (
            <div className="space-y-1.5" role="listbox">
              {searchResults.slice(0, 6).map((t, idx) => {
                const isSelected = idx === selectedIndex;
                return (
                  <div
                    key={t.train_no}
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => handleSelectTrain(t)}
                    onMouseEnter={() => setSelectedIndex(idx)}
                    className={`h-[56px] px-3.5 rounded-md border flex items-center justify-between cursor-pointer transition-colors duration-120 min-h-[56px] ${
                      isSelected
                        ? 'bg-[#15181D] border-[#F5A524]'
                        : 'bg-[#101216] border-[#23272F] hover:bg-[#15181D]'
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <AspectLamp
                        aspect={
                          t.status_lamp === 'green'
                            ? 'clear'
                            : t.status_lamp === 'amber'
                            ? 'caution'
                            : 'restrict'
                        }
                        size="sm"
                      />
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 font-mono text-xs font-bold text-[#E9EBEE]">
                          <span>{highlightMatch(t.train_no, debouncedQuery)}</span>
                          <span className="text-[#6B7480]">·</span>
                          <span className="truncate font-sans font-medium text-xs">
                            {highlightMatch(lang === 'HI' && t.name_hi ? t.name_hi : t.name, debouncedQuery)}
                          </span>
                        </div>
                        <div className="text-[11px] font-mono text-[#A3ABB6] flex items-center gap-2 pt-0.5">
                          <span>{t.route_short}</span>
                          <span className="text-[#6B7480]">·</span>
                          <span className="text-[#3DDC97]">{t.next_departure}</span>
                        </div>
                      </div>
                    </div>

                    <div className="shrink-0 flex items-center gap-2 pl-2">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#1B1F26] border border-[#23272F] text-[#A3ABB6]">
                        {t.type}
                      </span>
                      <ChevronRight className="w-4 h-4 text-[#6B7480]" />
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* STATE 6: Empty Input Groups (Recent & Popular) (M4) */}
          {!trimmed && (
            <div className="space-y-4">
              {/* RECENT SEARCHES GROUP (from localStorage, max 4, dismissible) */}
              {recents.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-[#6B7480] px-1">
                    <span className="flex items-center gap-1.5">
                      <Clock className="w-3 h-3 text-[#A3ABB6]" />
                      <span>{lang === 'HI' ? 'हाल की खोजें' : 'Recent Searches'}</span>
                    </span>
                  </div>
                  <div className="space-y-1.5">
                    {recents.map((r) => (
                      <div
                        key={r.id}
                        onClick={() => {
                          if (r.type === 'PNR' && r.pnrRaw) {
                            handlePnrDirect(r.pnrRaw);
                          } else {
                            closeModal();
                            navigate(`/track/${r.id}`);
                          }
                        }}
                        className="h-[52px] px-3 bg-[#101216] hover:bg-[#15181D] border border-[#23272F] hover:border-[#2E333D] rounded-md flex items-center justify-between cursor-pointer transition-colors duration-120 min-h-[52px]"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          {r.type === 'PNR' ? (
                            <Ticket className="w-4 h-4 text-[#F5A524] shrink-0" />
                          ) : (
                            <Train className="w-4 h-4 text-[#3DDC97] shrink-0" />
                          )}
                          <div className="min-w-0">
                            <div className="text-xs font-mono font-bold text-[#E9EBEE] flex items-center gap-2">
                              <span>{r.id}</span>
                              <span className="text-[#6B7480]">·</span>
                              <span className="truncate font-sans font-normal text-xs text-[#A3ABB6]">
                                {r.name}
                              </span>
                            </div>
                            {r.route && (
                              <div className="text-[10px] font-mono text-[#6B7480]">{r.route}</div>
                            )}
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={(e) => removeRecent(r.id, e)}
                          className="p-2 text-[#6B7480] hover:text-[#F4506A] min-w-[44px] min-h-[44px] flex items-center justify-center transition-colors"
                          aria-label="Remove search"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* POPULAR NOW GROUP (from /v1/passenger/popular - zero hardcoded data) */}
              {popularTrains && popularTrains.length > 0 && !isOffline && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-[#6B7480] px-1">
                    <span className="flex items-center gap-1.5">
                      <Flame className="w-3 h-3 text-[#F5A524]" />
                      <span>{lang === 'HI' ? 'वर्तमान में लोकप्रिय' : 'Popular Now'}</span>
                    </span>
                  </div>
                  <div className="space-y-1.5">
                    {popularTrains.slice(0, 5).map((p) => (
                      <div
                        key={p.train_no}
                        onClick={() => handleSelectTrain(p)}
                        className="h-[52px] px-3 bg-[#101216] hover:bg-[#15181D] border border-[#23272F] hover:border-[#2E333D] rounded-md flex items-center justify-between cursor-pointer transition-colors duration-120 min-h-[52px]"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <AspectLamp
                            aspect={
                              p.status_lamp === 'green'
                                ? 'clear'
                                : p.status_lamp === 'amber'
                                ? 'caution'
                                : 'restrict'
                            }
                            size="sm"
                          />
                          <div className="min-w-0">
                            <div className="text-xs font-mono font-bold text-[#E9EBEE] flex items-center gap-2">
                              <span>{p.train_no}</span>
                              <span className="text-[#6B7480]">·</span>
                              <span className="truncate font-sans font-medium text-xs">
                                {lang === 'HI' && p.name_hi ? p.name_hi : p.name}
                              </span>
                            </div>
                            <div className="text-[10px] font-mono text-[#A3ABB6] flex items-center gap-2">
                              <span>{p.route_short}</span>
                              <span className="text-[#6B7480]">·</span>
                              <span className="text-[#3DDC97]">{p.next_departure}</span>
                            </div>
                          </div>
                        </div>

                        <ChevronRight className="w-4 h-4 text-[#6B7480] shrink-0" />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer / Keyboard Shortcuts Legend */}
        <div className="p-3 bg-[#0A0B0D] border-t border-[#23272F] flex items-center justify-between text-[11px] font-mono text-[#6B7480]">
          <div className="flex items-center gap-3">
            <span className="hidden sm:inline">
              <kbd className="px-1.5 py-0.5 bg-[#15181D] border border-[#23272F] rounded text-[#A3ABB6]">↑</kbd>
              <kbd className="px-1.5 py-0.5 bg-[#15181D] border border-[#23272F] rounded text-[#A3ABB6] ml-1">↓</kbd>{' '}
              {lang === 'HI' ? 'नेविगेट करें' : 'to navigate'}
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 bg-[#15181D] border border-[#23272F] rounded text-[#A3ABB6]">↵</kbd>{' '}
              {lang === 'HI' ? 'चुनें' : 'to select'}
            </span>
          </div>
          <span>
            <kbd className="px-1.5 py-0.5 bg-[#15181D] border border-[#23272F] rounded text-[#A3ABB6]">ESC</kbd>{' '}
            {lang === 'HI' ? 'बंद करें' : 'to close'}
          </span>
        </div>
      </div>
    </div>
  );
};
