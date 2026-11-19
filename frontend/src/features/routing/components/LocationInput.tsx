import { useEffect, useId, useState } from 'react';
import { Check, LoaderCircle, MapPin } from 'lucide-react';
import { Field } from '../../../components/ui/Field';
import { errorMessage } from '../../../lib/apiClient';
import { searchLocations } from '../services/routingApi';
import type { ResolvedPlace } from '../types';

export function LocationInput({ id, label, value, selected, live, onChange, onSelect }: {
  id: string; label: string; value: string; selected?: ResolvedPlace; live: boolean;
  onChange: (text: string) => void; onSelect: (place: ResolvedPlace) => void;
}) {
  const listId = useId();
  const [focused, setFocused] = useState(false);
  const [matches, setMatches] = useState<ResolvedPlace[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [active, setActive] = useState(-1);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    setMatches([]); setError(null); setSearched(false); setActive(-1); setLoading(false);
    if (!live || !focused || selected || value.trim().length < 2) return;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      try {
        const response = await searchLocations(value.trim(), controller.signal);
        if (!controller.signal.aborted) {
          setMatches(response.results); setSearched(true);
        }
      } catch (caught) { if (!controller.signal.aborted) setError(errorMessage(caught)); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    }, 300);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [value, focused, selected, live, retry]);
  const open = live && focused && !selected && (loading || searched || error !== null);
  function choose(place: ResolvedPlace) { onSelect(place); setFocused(false); setMatches([]); }
  return <Field id={id} label={label} className="relative">
    <div className="relative">
      <MapPin className="pointer-events-none absolute top-3.5 left-3 size-4 text-muted" aria-hidden="true" />
      <input id={id} autoComplete="off" required maxLength={200} value={value}
        role={live ? 'combobox' : undefined} aria-autocomplete={live ? 'list' : undefined}
        aria-expanded={live ? open : undefined} aria-controls={live ? listId : undefined}
        aria-activedescendant={open && active >= 0 ? `${listId}-${active}` : undefined}
        className="field-input pr-8 pl-9" placeholder="Search city or address"
        onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}
        onChange={event => { onChange(event.target.value); setActive(-1); }}
        onKeyDown={event => {
          if (event.key === 'Escape') { setFocused(false); return; }
          if (!open || !matches.length) return;
          if (event.key === 'ArrowDown') { event.preventDefault(); setActive(index => (index + 1) % matches.length); }
          if (event.key === 'ArrowUp') { event.preventDefault(); setActive(index => (index <= 0 ? matches.length : index) - 1); }
          if (event.key === 'Enter') { event.preventDefault(); if (active >= 0) choose(matches[active]); }
        }} />
      {loading ? <LoaderCircle size={14} className="pointer-events-none absolute top-3.5 right-3 animate-spin text-muted" />
        : selected && <Check size={14} className="pointer-events-none absolute top-3.5 right-3 text-accent" />}
    </div>
    {open && <div className="absolute top-full right-0 left-0 z-40 mt-2 overflow-hidden rounded-lg border border-line bg-panel shadow-panel">
      {loading && <p role="status" className="p-3 text-xs text-muted">Searching locations…</p>}
      {error && <div className="p-3 text-xs"><p role="alert" className="text-severe">{error}</p>
        <button type="button" onMouseDown={event => event.preventDefault()} onClick={() => setRetry(value => value + 1)} className="mt-2 text-accent underline">Retry search</button></div>}
      {!loading && !error && searched && !matches.length && <p className="p-3 text-xs text-muted">No matching locations. Try a more specific address.</p>}
      <div id={listId} role="listbox" aria-label={`${label} suggestions`}>
        {matches.map((place, index) => <button type="button" role="option" aria-selected={active === index} id={`${listId}-${index}`}
          key={place.id} tabIndex={-1} onMouseDown={event => event.preventDefault()} onClick={() => choose(place)}
          className={`block w-full border-b border-line px-3 py-2.5 text-left last:border-0 hover:bg-field ${active === index ? 'bg-field' : ''}`}>
          <span className="block text-xs text-ink">{place.label}</span><span className="mt-1 block text-[10px] text-muted">{place.timeZone}</span>
        </button>)}
      </div>
      <p className="border-t border-line px-3 py-2 text-[9px] text-subtle">Powered by Geoapify · © OpenStreetMap contributors</p>
    </div>}
  </Field>;
}
