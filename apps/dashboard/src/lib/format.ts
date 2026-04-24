export function formatDate(isoString: string): string {
  const date = new Date(isoString);
  if (isNaN(date.getTime())) return isoString; // fallback if invalid

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  }).format(date);
}

export function truncateTraceId(id: string): string {
  if (!id || id.length <= 12) return id;
  return `${id.slice(0, 6)}...${id.slice(-6)}`;
}
