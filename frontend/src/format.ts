// Display formatters. Currency is rendered with the code (e.g. "SAR") rather
// than a locale symbol, matching the lender/finance context.

export function money(value: number, currency = "SAR"): string {
  return `${currency} ${value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function compactMoney(value: number, currency = "SAR"): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `${currency} ${(value / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${currency} ${(value / 1_000).toFixed(1)}K`;
  return `${currency} ${value.toFixed(0)}`;
}

export function pct(value: number, digits = 1): string {
  return `${value.toFixed(digits)}%`;
}

// A 0..1 share -> percentage string.
export function sharePct(share: number, digits = 1): string {
  return `${(share * 100).toFixed(digits)}%`;
}

export function titleize(snake: string): string {
  return snake
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function monthLabel(ym: string): string {
  // "2025-08" -> "Aug 25"
  const [y, m] = ym.split("-").map(Number);
  const name = new Date(y, (m ?? 1) - 1, 1).toLocaleString("en-US", {
    month: "short",
  });
  return `${name} ${String(y).slice(2)}`;
}
