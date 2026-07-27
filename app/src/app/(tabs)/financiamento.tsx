import { Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

import { FinanciamentoView } from '@/features/financiamento/financiamento-view';
import { ThemedText } from '@/components/themed-text';
import { useSession } from '@/features/auth/session';
import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius, Spacing, Typography } from '@/theme';

export default function FinanciamentoScreen() {
  const { colors } = useAppTheme();
  const { isAuthenticated } = useSession();
  const router = useRouter();

  // Atalho de login apenas para quem ainda não entrou.
  const entrar = isAuthenticated ? null : (
    <Pressable
      onPress={() => router.push('/login')}
      accessibilityRole="button"
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: Spacing.one,
        paddingVertical: Spacing.one,
        paddingHorizontal: Spacing.two,
        borderRadius: Radius.pill,
        backgroundColor: colors.brandSoft,
      }}>
      <Ionicons name="log-in-outline" size={16} color={colors.brand} />
      <ThemedText style={[Typography.label, { color: colors.brand }]}>Entrar</ThemedText>
    </Pressable>
  );

  return <FinanciamentoView headerRight={entrar} />;
}
