import { StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius, Spacing, Typography } from '@/theme';
import { ThemedText } from '@/components/themed-text';

type Props = {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  description?: string;
  /** Badge opcional (ex.: "Em construção"). */
  tag?: string;
};

export function EmptyState({ icon, title, description, tag }: Props) {
  const { colors } = useAppTheme();

  return (
    <View style={styles.wrap}>
      <View style={[styles.iconWrap, { backgroundColor: colors.brandSoft }]}>
        <Ionicons name={icon} size={40} color={colors.brand} />
      </View>

      <ThemedText style={[Typography.h2, { color: colors.text, textAlign: 'center' }]}>
        {title}
      </ThemedText>

      {description && (
        <ThemedText
          style={[
            Typography.body,
            { color: colors.textSecondary, textAlign: 'center', maxWidth: 320 },
          ]}>
          {description}
        </ThemedText>
      )}

      {tag && (
        <View style={[styles.tag, { backgroundColor: colors.warningSoft }]}>
          <Ionicons name="construct-outline" size={14} color={colors.warning} />
          <ThemedText style={[Typography.caption, { color: colors.warning }]}>{tag}</ThemedText>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.three,
    padding: Spacing.four,
  },
  iconWrap: {
    width: 88,
    height: 88,
    borderRadius: Radius.xl,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.one,
    paddingVertical: Spacing.one,
    paddingHorizontal: Spacing.two,
    borderRadius: Radius.pill,
    marginTop: Spacing.one,
  },
});
