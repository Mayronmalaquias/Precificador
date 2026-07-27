import { ActivityIndicator, Pressable, StyleSheet, View, type ViewStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius, Spacing, Typography } from '@/theme';
import { ThemedText } from '@/components/themed-text';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'md' | 'lg';

type Props = {
  label: string;
  onPress?: () => void;
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  disabled?: boolean;
  icon?: keyof typeof Ionicons.glyphMap;
  fullWidth?: boolean;
  style?: ViewStyle;
};

export function Button({
  label,
  onPress,
  variant = 'primary',
  size = 'lg',
  loading = false,
  disabled = false,
  icon,
  fullWidth = true,
  style,
}: Props) {
  const { colors } = useAppTheme();
  const isDisabled = disabled || loading;

  const height = size === 'lg' ? 54 : 46;
  const palette: Record<Variant, { bg: string; fg: string; border?: string }> = {
    primary: { bg: colors.brand, fg: colors.onBrand },
    secondary: { bg: colors.surfaceAlt, fg: colors.text, border: colors.border },
    ghost: { bg: 'transparent', fg: colors.brand },
    danger: { bg: colors.danger, fg: '#FFFFFF' },
  };
  const p = palette[variant];

  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      accessibilityRole="button"
      accessibilityState={{ disabled: isDisabled, busy: loading }}
      style={({ pressed }) => [
        styles.base,
        {
          height,
          backgroundColor: p.bg,
          borderColor: p.border ?? 'transparent',
          borderWidth: p.border ? StyleSheet.hairlineWidth : 0,
          width: fullWidth ? '100%' : undefined,
          opacity: isDisabled ? 0.55 : 1,
          transform: [{ scale: pressed && !isDisabled ? 0.98 : 1 }],
        },
        style,
      ]}>
      {loading ? (
        <ActivityIndicator color={p.fg} />
      ) : (
        <View style={styles.content}>
          {icon && <Ionicons name={icon} size={20} color={p.fg} />}
          <ThemedText style={[Typography.button, { color: p.fg }]}>{label}</ThemedText>
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: Spacing.four,
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
  },
});
