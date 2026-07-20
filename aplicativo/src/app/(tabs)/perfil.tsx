import { StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { Button } from '@/components/ui/button';
import { LoginGate } from '@/components/ui/login-gate';
import { Screen } from '@/components/ui/screen';
import { ThemedText } from '@/components/themed-text';
import { useSession } from '@/features/auth/session';
import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius, Spacing, Typography, shadow } from '@/theme';
import { confirmAction } from '@/utils/confirm';

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() ?? '').join('') || 'U';
}

export default function PerfilScreen() {
  const { colors, isDark } = useAppTheme();
  const { isAuthenticated, nomeUsuario, idCorretor, permissao, user, signOut } = useSession();

  if (!isAuthenticated) {
    return (
      <LoginGate title="Sua conta" description="Entre para acessar seu perfil e as ferramentas do corretor." />
    );
  }

  function confirmLogout() {
    confirmAction({
      title: 'Sair da conta',
      message: 'Deseja realmente sair?',
      confirmLabel: 'Sair',
      destructive: true,
      onConfirm: () => signOut(),
    });
  }

  const rows: { icon: keyof typeof Ionicons.glyphMap; label: string; value: string }[] = [
    { icon: 'id-card-outline', label: 'ID', value: idCorretor },
    { icon: 'shield-checkmark-outline', label: 'Permissão', value: permissao || 'corretor' },
    { icon: 'people-outline', label: 'Equipe', value: String(user?.team || '—') },
    { icon: 'at-outline', label: 'Usuário', value: String(user?.username || '—') },
  ];

  return (
    <Screen scroll edges={['top']}>
      <ThemedText style={[Typography.h1, { color: colors.text }]}>Perfil</ThemedText>

      <View
        style={[
          styles.card,
          shadow('sm', isDark),
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}>
        <View style={styles.header}>
          <View style={[styles.avatar, { backgroundColor: colors.brand }]}>
            <ThemedText style={[Typography.h2, { color: colors.onBrand }]}>
              {initials(nomeUsuario)}
            </ThemedText>
          </View>
          <View style={styles.headerText}>
            <ThemedText style={[Typography.title, { color: colors.text }]} numberOfLines={1}>
              {nomeUsuario}
            </ThemedText>
            <View style={[styles.badge, { backgroundColor: colors.brandSoft }]}>
              <ThemedText style={[Typography.caption, { color: colors.brand }]}>
                {(permissao || 'corretor').toUpperCase()}
              </ThemedText>
            </View>
          </View>
        </View>

        <View style={[styles.divider, { backgroundColor: colors.border }]} />

        {rows.map((r) => (
          <View key={r.label} style={styles.row}>
            <Ionicons name={r.icon} size={20} color={colors.textMuted} />
            <ThemedText style={[Typography.body, { color: colors.textSecondary, flex: 1 }]}>
              {r.label}
            </ThemedText>
            <ThemedText style={[Typography.bodyBold, { color: colors.text }]} numberOfLines={1}>
              {r.value}
            </ThemedText>
          </View>
        ))}
      </View>

      <Button label="Sair da conta" variant="secondary" icon="log-out-outline" onPress={confirmLogout} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: Radius.xl,
    borderWidth: StyleSheet.hairlineWidth,
    padding: Spacing.four,
    gap: Spacing.three,
  },
  header: { flexDirection: 'row', alignItems: 'center', gap: Spacing.three },
  avatar: {
    width: 60,
    height: 60,
    borderRadius: Radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerText: { flex: 1, gap: Spacing.one },
  badge: {
    alignSelf: 'flex-start',
    paddingVertical: 2,
    paddingHorizontal: Spacing.two,
    borderRadius: Radius.pill,
  },
  divider: { height: StyleSheet.hairlineWidth },
  row: { flexDirection: 'row', alignItems: 'center', gap: Spacing.three },
});
