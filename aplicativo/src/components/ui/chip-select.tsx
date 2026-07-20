import { Pressable, ScrollView, StyleSheet, View } from 'react-native';

import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius, Spacing, Typography } from '@/theme';
import { ThemedText } from '@/components/themed-text';

export type ChipOption<T extends string | number = string> = { label: string; value: T };

type Props<T extends string | number> = {
  label?: string;
  options: ChipOption<T>[];
  value: T;
  onChange: (value: T) => void;
  /** true = rola na horizontal (listas longas, ex.: bairros). */
  scroll?: boolean;
  disabled?: boolean;
};

export function ChipSelect<T extends string | number>({
  label,
  options,
  value,
  onChange,
  scroll = false,
  disabled = false,
}: Props<T>) {
  const { colors } = useAppTheme();

  const chips = options.map((opt) => {
    const active = opt.value === value;
    return (
      <Pressable
        key={String(opt.value)}
        onPress={() => !disabled && onChange(opt.value)}
        disabled={disabled}
        accessibilityRole="button"
        accessibilityState={{ selected: active }}
        style={({ pressed }) => [
          styles.chip,
          {
            backgroundColor: active ? colors.brand : colors.surfaceAlt,
            borderColor: active ? colors.brand : colors.border,
            opacity: pressed && !disabled ? 0.85 : 1,
          },
        ]}>
        <ThemedText
          style={[Typography.label, { color: active ? colors.onBrand : colors.textSecondary }]}>
          {opt.label}
        </ThemedText>
      </Pressable>
    );
  });

  return (
    <View style={styles.group}>
      {label && (
        <ThemedText style={[Typography.label, { color: colors.textSecondary }]}>
          {label}
        </ThemedText>
      )}
      {scroll ? (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.row}>
          {chips}
        </ScrollView>
      ) : (
        <View style={[styles.row, styles.wrap]}>{chips}</View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  group: { gap: Spacing.two },
  row: { flexDirection: 'row', gap: Spacing.two },
  wrap: { flexWrap: 'wrap' },
  chip: {
    paddingVertical: Spacing.two,
    paddingHorizontal: Spacing.three,
    borderRadius: Radius.pill,
    borderWidth: StyleSheet.hairlineWidth,
  },
});
