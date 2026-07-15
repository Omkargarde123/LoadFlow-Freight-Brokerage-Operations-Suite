export function statusClass(status) {
  return "status-" + status.replace(/\//g, "-").replace(/\s+/g, "-");
}

export function formatDate(d) {
  if (!d) return "—";
  const date = new Date(d);
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function formatDateTime(d) {
  if (!d) return "—";
  const date = new Date(d);
  return date.toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

export const STATUS_SEQUENCE = [
  "Posted", "Carrier Assigned", "Rate Confirmed", "Dispatched",
  "In Transit", "Delivered", "POD Verified", "Invoiced/Closed",
];

export function nextStatus(current) {
  const idx = STATUS_SEQUENCE.indexOf(current);
  if (idx === -1 || idx === STATUS_SEQUENCE.length - 1) return null;
  return STATUS_SEQUENCE[idx + 1];
}
