import { Pressable, StyleSheet, View } from 'react-native';

import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius, Spacing, Typography } from '@/theme';
import { ThemedText } from '@/components/themed-text';

const LEGENDAS: Record<number, string> = {
  1: 'Péssimo',
  2: 'Muito ruim',
  3: 'Ruim',
  4: 'Regular',
  5: 'Médio',
  6: 'Razoável',
  7: 'Bom',
  8: 'Muito bom',
  9: 'Ótimo',
  10: 'Excelente',
};

type Props = {
  label: string;
  value: number;
  onChange: (value: number) => void;
};

/** Seletor de nota 1–10 (avaliações da visita). */
export function NotaSelector({ label, value, onChange }: Props) {
  const { colors } = useAppTheme();

  return (
    <View style={styles.group}>
      <ThemedText style={[Typography.label, { color: colors.text }]}>{label}</ThemedText>
      <View style={styles.grid}>
        {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => {
          const active = value === n;
          return (
            <Pressable
              key={n}
              onPress={() => onChange(n)}
              accessibilityRole="button"
              accessibilityLabel={`Nota ${n}: ${LEGENDAS[n]}`}
              accessibilityState={{ selected: active }}
              style={({ pressed }) => [
                styles.cell,
                {
                  backgroundColor: active ? colors.brand : colors.surfaceAlt,
                  borderColor: active ? colors.brand : colors.border,
                  opacity: pressed && !active ? 0.7 : 1,
                },
              ]}>
              <ThemedText
                style={[
                  Typography.bodyBold,
                  { color: active ? colors.onBrand : colors.textSecondary },
                ]}>
                {n}
              </ThemedText>
            </Pressable>
          );
        })}
      </View>
      {value > 0 && (
        <ThemedText style={[Typography.caption, { color: colors.textMuted }]}>
          {value} — {LEGENDAS[value]}
        </ThemedText>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  group: { gap: Spacing.two },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.one + 2 },
  cell: {
    width: 44,
    height: 44,
    borderRadius: Radius.sm,
    borderWidth: StyleSheet.hairlineWidth,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
