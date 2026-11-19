import { useCallback, useEffect, useState } from 'react';
import type { DataMode } from '../../routing/types';

export function useForecastPlayback(enabled: boolean, resetKey: string, mode: DataMode) {
  const [timelines, setTimelines] = useState<Partial<Record<DataMode, { key: string; hour: number }>>>({});
  const hour = timelines[mode]?.key === resetKey ? timelines[mode]!.hour : 0;
  const [playing, setPlaying] = useState(false);
  useEffect(() => {
    if (!playing || !enabled) return;
    const timer = window.setInterval(() => setTimelines(current => {
      const previous = current[mode]?.key === resetKey ? current[mode]!.hour : 0;
      return { ...current, [mode]: { key: resetKey, hour: previous >= 48 ? 0 : previous + 1 } };
    }), 750);
    return () => window.clearInterval(timer);
  }, [playing, enabled, resetKey, mode]);
  useEffect(() => { setPlaying(false); }, [resetKey]);
  useEffect(() => { if (!enabled) setPlaying(false); }, [enabled]);
  const seek = useCallback((next: number) => {
    setTimelines(current => ({ ...current, [mode]: { key: resetKey, hour: next } }));
    setPlaying(false);
  }, [resetKey, mode]);
  return { hour, playing, seek, toggle: () => setPlaying(current => !current) };
}
