// Pure display helpers: no DOM, so they are easy to test.

const STATUS_LABELS = {
  placed: "Placed",
  shipped: "Shipped",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

export function formatMoney(cents) {
  if (!Number.isInteger(cents) || cents < 0) throw new RangeError(`not an amount in cents: ${cents}`);
  const dollars = Math.floor(cents / 100);
  const rest = String(cents % 100).padStart(2, "0");
  return `$${dollars.toLocaleString("en-US")}.${rest}`;
}

export function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toISOString().slice(0, 10);
}

export function statusLabel(status) {
  return STATUS_LABELS[status] ?? status;
}

// Only an order that has not shipped can be cancelled; the API enforces the same rule.
export function canCancel(order) {
  return order.status === "placed";
}

export function itemSummary(order) {
  const units = order.items.reduce((n, i) => n + i.quantity, 0);
  return `${units} ${units === 1 ? "item" : "items"}`;
}
