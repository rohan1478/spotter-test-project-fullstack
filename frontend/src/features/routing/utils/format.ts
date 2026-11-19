export const formatDuration = (minutes: number) => `${Math.floor(Math.round(minutes) / 60)}h ${String(Math.round(minutes) % 60).padStart(2, '0')}m`;
export const formatNumber = (value: number, digits = 1) => new Intl.NumberFormat('en-US', { maximumFractionDigits: digits }).format(value);
export const formatReading = (value: number | null, unit: string) => value === null ? 'Unavailable' : `${formatNumber(value, 2)} ${unit}`;

export function formatTime(date: string, timeZone = 'America/Chicago') {
  return new Intl.DateTimeFormat('en-US', {
    hour: '2-digit', minute: '2-digit', hour12: false, timeZoneName: 'short', timeZone,
  }).format(new Date(date));
}

export function formatForecast(date: string, hour: number, timeZone = 'UTC') {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    hour12: false, timeZoneName: 'short', timeZone,
  }).format(new Date(new Date(date).getTime() + hour * 3_600_000));
}

export function localDateTime(date: Date, timeZone: string) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(date);
  const get = (key: string) => parts.find(part => part.type === key)!.value;
  return `${get('year')}-${get('month')}-${get('day')}T${get('hour')}:${get('minute')}`;
}

export function departureToISOString(value: string, timeZone: string) {
  const [year, month, day, hour, minute] = value.split(/[-T:]/).map(Number);
  const target = Date.UTC(year, month - 1, day, hour, minute);
  let instant = target;
  for (let i = 0; i < 3; i++) {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone, year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    }).formatToParts(new Date(instant));
    const get = (type: string) => Number(parts.find((part) => part.type === type)?.value);
    const represented = Date.UTC(get('year'), get('month') - 1, get('day'), get('hour'), get('minute'));
    instant += target - represented;
  }
  return new Date(instant).toISOString();
}
