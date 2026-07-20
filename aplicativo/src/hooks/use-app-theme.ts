import { useMemo } from 'react';

import { useColorScheme } from '@/hooks/use-color-scheme';
import { Palette, type AppColors } from '@/theme';

export type AppTheme = {
  colors: AppColors;
  isDark: boolean;
  scheme: 'light' | 'dark';
};

/** Tema resolvido (cores + flag dark) reativo ao esquema do sistema. */
export function useAppTheme(): AppTheme {
  const raw = useColorScheme();
  const scheme = raw === 'dark' ? 'dark' : 'light';

  return useMemo(
    () => ({ colors: Palette[scheme], isDark: scheme === 'dark', scheme }),
    [scheme],
  );
}
