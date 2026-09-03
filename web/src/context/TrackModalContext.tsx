import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';

interface TrackModalContextType {
  isOpen: boolean;
  openModal: (initialInput?: string, trigger?: HTMLElement) => void;
  closeModal: () => void;
  toggleModal: () => void;
  initialInput: string;
  lang: 'EN' | 'HI';
  setLang: (lang: 'EN' | 'HI') => void;
}

const TrackModalContext = createContext<TrackModalContextType | undefined>(undefined);

export function TrackModalProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [initialInput, setInitialInput] = useState('');
  const [lang, setLangState] = useState<'EN' | 'HI'>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('railtwin_passenger_lang');
      if (saved === 'HI' || saved === 'EN') return saved;
    }
    return 'EN';
  });

  const triggerRef = useRef<HTMLElement | null>(null);

  const setLang = useCallback((newLang: 'EN' | 'HI') => {
    setLangState(newLang);
    if (typeof window !== 'undefined') {
      localStorage.setItem('railtwin_passenger_lang', newLang);
    }
  }, []);

  const openModal = useCallback((input?: string, trigger?: HTMLElement) => {
    // Record trigger element for focus return
    if (trigger) {
      triggerRef.current = trigger;
    } else if (typeof document !== 'undefined' && document.activeElement instanceof HTMLElement) {
      triggerRef.current = document.activeElement;
    }
    setInitialInput(input || '');
    setIsOpen(true);
  }, []);

  const closeModal = useCallback(() => {
    setIsOpen(false);
    // Return focus to trigger element (A1)
    setTimeout(() => {
      if (triggerRef.current && typeof triggerRef.current.focus === 'function') {
        triggerRef.current.focus();
      }
    }, 50);
  }, []);

  const toggleModal = useCallback(() => {
    if (isOpen) {
      closeModal();
    } else {
      openModal();
    }
  }, [isOpen, openModal, closeModal]);

  // Global ⌘K / Ctrl+K shortcut (E3)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        toggleModal();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggleModal]);

  return (
    <TrackModalContext.Provider
      value={{
        isOpen,
        openModal,
        closeModal,
        toggleModal,
        initialInput,
        lang,
        setLang,
      }}
    >
      {children}
    </TrackModalContext.Provider>
  );
}

export function useTrackModal() {
  const context = useContext(TrackModalContext);
  if (!context) {
    throw new Error('useTrackModal must be used within a TrackModalProvider');
  }
  return context;
}
