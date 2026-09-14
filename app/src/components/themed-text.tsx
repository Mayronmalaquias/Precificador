import { Text, type TextProps } from 'react-native';

import { useAppTheme } from '@/hooks/use-app-theme';
import type { AppColors } from '@/theme';

export type ThemedTextProps = TextProps & {
  /** Cor da paleta da 61. Padrão `text`. */
  themeColor?: keyof AppColors;
};

/**
 * `Text` com a cor do tema resolvida.
 *
 * Lia a paleta do template (`constants/theme.Colors`, preto e branco puros) enquanto o
 * resto do app usava a da 61 (`theme.Palette`) — por isso cada chamada precisava repetir
 * `{ color: colors.text }` para corrigir o padrao. Com a paleta certa aqui, o padrao serve
 * e as 34 repeticoes saem.
 *
 * As variantes de tamanho (`type="title" | "small" | ...`) foram removidas junto: nenhuma
 * era passada, e os 94 usos ja trazem `Typography.*`, que as sobrescrevia de qualquer jeito.
 */
export function ThemedText({ style, themeColor = 'text', ...rest }: ThemedTextProps) {
  const { colors } = useAppTheme();

  return <Text style={[{ color: colors[themeColor] }, style]} {...rest} />;
}
