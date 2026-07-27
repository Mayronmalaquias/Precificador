import type { AppColors } from '@/theme';
import type { StatusCaptacao } from '@/features/captacao/api';

export function statusMeta(status: StatusCaptacao, colors: AppColors) {
  switch (status) {
    case 'fechado':
      return { label: 'Fechado', color: colors.textMuted, soft: colors.surfaceAlt };
    case 'exclusividade':
      return { label: 'Exclusividade', color: colors.success, soft: colors.successSoft };
    default:
      return { label: 'Ativo', color: colors.brand, soft: colors.brandSoft };
  }
}

export function formatDateBR(iso?: string | null): string {
  if (!iso) return '—';
  const d = String(iso).slice(0, 10).split('-');
  return d.length === 3 ? `${d[2]}/${d[1]}/${d[0]}` : String(iso);
}

/** Dias desde a entrada na etapa atual. */
export function diasNaEtapa(dataEntrada?: string | null): number | null {
  if (!dataEntrada) return null;
  const t = new Date(dataEntrada).getTime();
  if (Number.isNaN(t)) return null;
  return Math.max(0, Math.floor((Date.now() - t) / 86400000));
}
