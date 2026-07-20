/**
 * Design system do app 61.
 *
 * Fonte da verdade para cor, espaçamento, raio, tipografia e sombra.
 * Mantido separado de `@/constants/theme` (scaffold) para não quebrar os
 * componentes de demonstração; reaproveitamos apenas a escala `Spacing` (4/8px).
 */
import { Platform, type TextStyle, type ViewStyle } from 'react-native';

import { Spacing } from '@/constants/theme';

export { Spacing };

/** Paleta semântica. Toda chave existe em light e dark (contrato do useAppTheme). */
export const Palette = {
  light: {
    // Marca 61: rosa + branco
    brand: '#E1005B',
    brandPressed: '#B80049',
    brandSoft: '#FFE5EF',
    onBrand: '#FFFFFF',

    canvas: '#F8F6F7',
    surface: '#FFFFFF',
    surfaceAlt: '#F2EEF0',

    border: '#EBE4E8',
    borderStrong: '#D6CCD2',

    text: '#0F172A',
    textSecondary: '#5B6472',
    textMuted: '#8A93A2',
    placeholder: '#9AA3B2',

    inputBg: '#FFFFFF',

    danger: '#E5484D',
    dangerSoft: '#FDECEC',
    success: '#2E9E5B',
    successSoft: '#E6F5EC',
    warning: '#E5900A',
    warningSoft: '#FDF3E2',

    overlay: 'rgba(15,23,42,0.45)',
    skeleton: '#E7EAEF',
  },
  dark: {
    brand: '#FF4D8D',
    brandPressed: '#E33E7B',
    brandSoft: '#3A1020',
    onBrand: '#FFFFFF',

    canvas: '#0B0F14',
    surface: '#151A21',
    surfaceAlt: '#1D242D',

    border: '#262E38',
    borderStrong: '#333C48',

    text: '#F4F6F8',
    textSecondary: '#AEB6C2',
    textMuted: '#7C8695',
    placeholder: '#6B7482',

    inputBg: '#111720',

    danger: '#FF6369',
    dangerSoft: '#2A1416',
    success: '#4CC97E',
    successSoft: '#10261A',
    warning: '#F5B14C',
    warningSoft: '#2A1F0E',

    overlay: 'rgba(0,0,0,0.6)',
    skeleton: '#1E252E',
  },
} as const;

export type AppColorName = keyof typeof Palette.light & keyof typeof Palette.dark;
/** Valores widened para string: light e dark são ambos atribuíveis. */
export type AppColors = { [K in keyof typeof Palette.light]: string };

/** Raio de canto — consistente em todo o app. */
export const Radius = {
  xs: 6,
  sm: 10,
  md: 14,
  lg: 18,
  xl: 24,
  pill: 999,
} as const;

/** Escala tipográfica (peso/altura de linha calibrados para mobile). */
export const Typography = {
  display: { fontSize: 32, lineHeight: 38, fontWeight: '700' },
  h1: { fontSize: 26, lineHeight: 32, fontWeight: '700' },
  h2: { fontSize: 22, lineHeight: 28, fontWeight: '700' },
  title: { fontSize: 18, lineHeight: 24, fontWeight: '600' },
  body: { fontSize: 16, lineHeight: 24, fontWeight: '400' },
  bodyBold: { fontSize: 16, lineHeight: 24, fontWeight: '600' },
  label: { fontSize: 14, lineHeight: 20, fontWeight: '600' },
  caption: { fontSize: 13, lineHeight: 18, fontWeight: '500' },
  button: { fontSize: 16, lineHeight: 20, fontWeight: '700' },
} as const satisfies Record<string, TextStyle>;

/** Sombras suaves. Em dark viram elevação sutil (sombra escura some no fundo). */
export function shadow(level: 'sm' | 'md' | 'lg', isDark = false): ViewStyle {
  if (Platform.OS === 'web') {
    // react-native-web usa boxShadow (shadow* é deprecado no web).
    const web: Record<typeof level, ViewStyle> = {
      sm: { boxShadow: isDark ? '0 2px 6px rgba(0,0,0,0.4)' : '0 2px 6px rgba(15,23,42,0.06)' },
      md: { boxShadow: isDark ? '0 6px 14px rgba(0,0,0,0.5)' : '0 6px 14px rgba(15,23,42,0.1)' },
      lg: { boxShadow: isDark ? '0 12px 24px rgba(0,0,0,0.55)' : '0 12px 24px rgba(15,23,42,0.14)' },
    };
    return web[level];
  }
  if (isDark) {
    // Dark mode: sombra quase imperceptível; a hierarquia vem do surfaceAlt/border.
    return { elevation: level === 'lg' ? 8 : level === 'md' ? 4 : 2 };
  }
  const map: Record<typeof level, ViewStyle> = {
    sm: {
      shadowColor: '#0F172A',
      shadowOpacity: 0.06,
      shadowRadius: 6,
      shadowOffset: { width: 0, height: 2 },
      elevation: 2,
    },
    md: {
      shadowColor: '#0F172A',
      shadowOpacity: 0.1,
      shadowRadius: 14,
      shadowOffset: { width: 0, height: 6 },
      elevation: 5,
    },
    lg: {
      shadowColor: '#0F172A',
      shadowOpacity: 0.14,
      shadowRadius: 24,
      shadowOffset: { width: 0, height: 12 },
      elevation: 10,
    },
  };
  return map[level];
}

export const Fonts = Platform.select({
  ios: { sans: 'system-ui', rounded: 'ui-rounded', mono: 'ui-monospace' },
  default: { sans: 'normal', rounded: 'normal', mono: 'monospace' },
});
