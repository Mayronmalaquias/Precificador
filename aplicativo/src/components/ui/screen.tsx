import type { ReactNode } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  View,
  type ViewStyle,
} from 'react-native';
import { SafeAreaView, type Edge } from 'react-native-safe-area-context';

import { useAppTheme } from '@/hooks/use-app-theme';
import { Spacing } from '@/theme';

type Props = {
  children: ReactNode;
  scroll?: boolean;
  /** Envolve em KeyboardAvoidingView (telas com formulário). */
  keyboardAvoiding?: boolean;
  edges?: readonly Edge[];
  contentStyle?: ViewStyle;
  padded?: boolean;
};

export function Screen({
  children,
  scroll = false,
  keyboardAvoiding = false,
  edges = ['top', 'bottom'],
  contentStyle,
  padded = true,
}: Props) {
  const { colors } = useAppTheme();

  const inner = scroll ? (
    <ScrollView
      style={styles.flex}
      contentContainerStyle={[padded && styles.padded, contentStyle]}
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}>
      {children}
    </ScrollView>
  ) : (
    <View style={[styles.flex, padded && styles.padded, contentStyle]}>{children}</View>
  );

  const body = keyboardAvoiding ? (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      {inner}
    </KeyboardAvoidingView>
  ) : (
    inner
  );

  return (
    <SafeAreaView edges={edges} style={[styles.flex, { backgroundColor: colors.canvas }]}>
      {body}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  padded: {
    padding: Spacing.four,
    gap: Spacing.three,
  },
});
