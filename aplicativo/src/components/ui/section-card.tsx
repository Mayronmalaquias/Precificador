import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius, Spacing, Typography, shadow } from '@/theme';
import { ThemedText } from '@/components/themed-text';

type Props = {
  title: string;
  icon: keyof typeof Ionicons.glyphMap;
  children: ReactNode;
};

/** Cartão de seção com cabeçalho — usado em formulários longos. */
export function SectionCard({ title, icon, children }: Props) {
  const { colors, isDark } = useAppTheme();
  return (
    <View
      style={[
        styles.card,
        shadow('sm', isDark),
        { backgroundColor: colors.surface, borderColor: colors.border },
      ]}>
      <View style={styles.header}>
        <View style={[styles.iconWrap, { backgroundColor: colors.brandSoft }]}>
          <Ionicons name={icon} size={18} color={colors.brand} />
        </View>
        <ThemedText style={[Typography.title, { color: colors.text }]}>{title}</ThemedText>
      </View>
      <View style={styles.body}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: Radius.xl,
    borderWidth: StyleSheet.hairlineWidth,
    padding: Spacing.four,
    gap: Spacing.three,
  },
  header: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  iconWrap: {
    width: 32,
    height: 32,
    borderRadius: Radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  body: { gap: Spacing.three },
});
