const DASH = '—';

export function formatBRL(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return DASH;
  try {
    return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  } catch {
    return `R$ ${value.toFixed(2)}`;
  }
}

export function formatNumber(value?: number | null, digits = 0): string {
  if (value == null || Number.isNaN(value)) return DASH;
  try {
    return value.toLocaleString('pt-BR', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  } catch {
    return value.toFixed(digits);
  }
}

export function formatM2(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return DASH;
  return `${formatNumber(value, 2)} m²`;
}

/** Recebe fração (0..1) e devolve percentual. */
export function formatPercent(fraction?: number | null): string {
  if (fraction == null || Number.isNaN(fraction)) return DASH;
  return `${formatNumber(fraction * 100, 2)}%`;
}
