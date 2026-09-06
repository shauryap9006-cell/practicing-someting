import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import type { PopularTrain, SearchResult } from '../lib/types';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
}) => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [popularTrains, setPopularTrains] = useState<PopularTrain[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input on open & load popular trains
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);

      // Fetch popular trains if not loaded
      if (popularTrains.length === 0) {
        api.passenger.popular()
          .then((data) => setPopularTrains(data))
          .catch(() => {
            // Keep empty on error
          });
      }
    }
  }, [isOpen]);

  // Global key listener for Escape and Arrow keys
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Query search when user types
  useEffect(() => {
    if (!query.trim()) {
      setSearchResults([]);
      setSelectedIndex(0);
      return;
    }

    setLoading(true);
    const timer = setTimeout(() => {
      api.passenger.search(query)
        .then((res) => {
          setSearchResults(res);
          setSelectedIndex(0);
        })
        .catch(() => {
          setSearchResults([]);
        })
        .finally(() => setLoading(false));
    }, 150);

    return () => clearTimeout(timer);
  }, [query]);

  if (!isOpen) return null;

  // Active items list: search results or popular trains
  const items = query.trim()
    ? searchResults.map((r) => ({
        train_no: r.train_no,
        name: r.name,
        route_short: r.route_short,
        delay_min: r.delay_min ?? r.last_delay,
      }))
    : popularTrains.map((p) => ({
        train_no: p.train_no,
        name: p.name,
        route_short: p.route_short,
        delay_min: p.delay_min,
      }));

  const handleSelect = (trainNo: string) => {
    onClose();
    navigate(`/t/${trainNo}`);
  };

  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (items.length > 0 ? (prev + 1) % items.length : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (items.length > 0 ? (prev - 1 + items.length) % items.length : 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (items[selectedIndex]) {
        handleSelect(items[selectedIndex].train_no);
      } else if (query.trim()) {
        handleSelect(query.trim());
      }
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-ink/40 flex items-start justify-center pt-16 sm:pt-24 px-4 backdrop-blur-[1px]"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl bg-surface border border-line rounded-[4px] overflow-hidden flex flex-col select-none animate-in fade-in zoom-in-95 duration-100"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3 border-b border-line bg-surface">
          <span className="font-mono text-xs text-muted pr-2">FIND</span>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleInputKeyDown}
            placeholder="Enter train number or name (e.g. 12301, Rajdhani, Shatabdi)..."
            className="w-full font-mono text-sm bg-transparent text-ink placeholder:text-muted focus:outline-none"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="text-xs font-mono text-muted hover:text-ink px-1 cursor-pointer"
            >
              CLEAR
            </button>
          )}
          <span className="font-mono text-[10px] text-muted pl-2 border-l border-line/60">
            ESC
          </span>
        </div>

        {/* Section Header */}
        <div className="px-4 py-1.5 bg-raised/60 border-b border-line/60 flex items-center justify-between text-[10px] font-mono text-muted uppercase tracking-wider">
          <span>{query.trim() ? 'Search Results' : 'Corridor Fleet / Popular Trains'}</span>
          {loading && <span>SEARCHING...</span>}
        </div>

        {/* Results List */}
        <div className="max-h-80 overflow-y-auto divide-y divide-line/40">
          {items.length === 0 ? (
            <div className="p-6 text-center font-mono text-xs text-muted">
              {loading
                ? 'Querying corridor database...'
                : query.trim()
                ? `No trains found matching "${query}". Press Enter to view train #${query}.`
                : 'No train records available.'}
            </div>
          ) : (
            items.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              const delay = item.delay_min ?? 0;

              return (
                <div
                  key={item.train_no}
                  onClick={() => handleSelect(item.train_no)}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`px-4 py-2.5 flex items-center justify-between cursor-pointer transition-colors ${
                    isSelected ? 'bg-raised text-ink' : 'hover:bg-raised/40 text-ink'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono font-bold text-xs px-2 py-0.5 bg-surface border border-line rounded-[2px] tabular-nums">
                      #{item.train_no}
                    </span>
                    <div className="flex flex-col">
                      <span className="font-sans text-xs font-medium text-ink leading-tight">
                        {item.name}
                      </span>
                      {item.route_short && (
                        <span className="font-mono text-[10px] text-muted">
                          {item.route_short}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {delay > 0 ? (
                      <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-[2px] border border-restrict/30 bg-restrict/5 text-restrict tabular-nums">
                        +{delay}m
                      </span>
                    ) : (
                      <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-[2px] border border-clear/30 bg-clear/5 text-clear">
                        Right Time
                      </span>
                    )}
                    <span className="font-mono text-[10px] text-muted">↵</span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer info */}
        <div className="px-4 py-2 bg-raised/30 border-t border-line/60 flex items-center justify-between text-[10px] font-mono text-muted">
          <span>↑↓ to navigate · Enter to select · Esc to close</span>
          <span>FastAPI :8000</span>
        </div>
      </div>
    </div>
  );
};
