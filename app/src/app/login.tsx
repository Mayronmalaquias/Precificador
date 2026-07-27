import { useRef, useState } from 'react';
import { Pressable, StyleSheet, TextInput, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Image } from 'expo-image';
import { Ionicons } from '@expo/vector-icons';

import { Button } from '@/components/ui/button';
import { Screen } from '@/components/ui/screen';
import { TextField } from '@/components/ui/text-field';
import { useToast } from '@/components/ui/toast';
import { ThemedText } from '@/components/themed-text';
import { useSession } from '@/features/auth/session';
import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius, Spacing, Typography, shadow } from '@/theme';

const LOGO = require('@/assets/images/logo-wordmark.png');

export default function LoginScreen() {
  const { colors, isDark } = useAppTheme();
  const { signIn } = useSession();
  const toast = useToast();
  const router = useRouter();
  const senhaRef = useRef<TextInput>(null);

  function fechar() {
    // Login é sempre empurrado a partir das tabs, então back volta ao Precificador.
    if (router.canGoBack()) router.back();
  }

  const [username, setUsername] = useState('');
  const [senha, setSenha] = useState('');
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState('');

  const canSubmit = username.trim().length > 0 && senha.length > 0 && !loading;

  async function handleSubmit() {
    if (loading) return;
    setErro('');

    if (!username.trim() || !senha) {
      setErro('Preencha usuário e senha.');
      return;
    }

    setLoading(true);
    try {
      await signIn(username.trim(), senha);
      toast.show({ type: 'success', message: 'Bem-vindo de volta!' });
      // A guarda de rota (Stack.Protected) fecha o login automaticamente ao autenticar.
    } catch (err: any) {
      const message = err?.message || 'Erro de conexão com o servidor.';
      setErro(message);
      toast.show({ type: 'error', message });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Screen keyboardAvoiding scroll padded={false} edges={['top', 'bottom']}>
      <View style={styles.container}>
        {/* Barra: fechar e voltar ao Precificador público */}
        <View style={styles.topBar}>
          <Pressable
            onPress={fechar}
            hitSlop={12}
            accessibilityRole="button"
            accessibilityLabel="Fechar"
            style={[styles.closeBtn, { backgroundColor: colors.surfaceAlt }]}>
            <Ionicons name="close" size={22} color={colors.textSecondary} />
          </Pressable>
        </View>

        {/* Hero / marca */}
        <View style={styles.hero}>
          <View style={[styles.logoCard, shadow('md', isDark)]}>
            <Image source={LOGO} style={styles.logo} contentFit="contain" transition={200} />
          </View>
          <ThemedText style={[Typography.display, { color: colors.text }]}>Entrar</ThemedText>
          <ThemedText style={[Typography.body, { color: colors.textSecondary }]}>
            Acesse sua conta para continuar
          </ThemedText>
        </View>

        {/* Formulário */}
        <View
          style={[
            styles.card,
            shadow('md', isDark),
            { backgroundColor: colors.surface, borderColor: colors.border },
          ]}>
          <TextField
            label="Usuário"
            icon="person-outline"
            placeholder="Digite seu usuário"
            value={username}
            onChangeText={(t) => {
              setUsername(t);
              if (erro) setErro('');
            }}
            autoCapitalize="none"
            autoCorrect={false}
            autoComplete="username"
            textContentType="username"
            returnKeyType="next"
            editable={!loading}
            onSubmitEditing={() => senhaRef.current?.focus()}
          />

          <TextField
            ref={senhaRef}
            label="Senha"
            icon="lock-closed-outline"
            placeholder="Digite sua senha"
            value={senha}
            onChangeText={(t) => {
              setSenha(t);
              if (erro) setErro('');
            }}
            password
            autoComplete="current-password"
            textContentType="password"
            returnKeyType="go"
            editable={!loading}
            onSubmitEditing={handleSubmit}
          />

          {erro ? (
            <View style={[styles.alert, { backgroundColor: colors.dangerSoft }]}>
              <ThemedText style={[Typography.caption, { color: colors.danger }]}>
                {erro}
              </ThemedText>
            </View>
          ) : null}

          <ThemedText
            onPress={() =>
              toast.show({
                type: 'info',
                message: 'Para recuperar a senha, fale com o RH da 61.',
              })
            }
            style={[Typography.label, styles.forgot, { color: colors.brand }]}>
            Esqueceu a senha?
          </ThemedText>
        </View>

        <View style={styles.flexSpacer} />

        {/* CTA na thumb zone */}
        <View style={styles.cta}>
          <Button
            label={loading ? 'Entrando...' : 'Entrar'}
            onPress={handleSubmit}
            loading={loading}
            disabled={!canSubmit}
            icon={loading ? undefined : 'arrow-forward'}
          />
        </View>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: Spacing.four,
    gap: Spacing.four,
    minHeight: 560,
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
  },
  closeBtn: {
    width: 40,
    height: 40,
    borderRadius: Radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  hero: {
    alignItems: 'center',
    gap: Spacing.two,
    marginTop: Spacing.two,
  },
  logoCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: Radius.lg,
    paddingHorizontal: Spacing.four,
    paddingVertical: Spacing.three,
    marginBottom: Spacing.three,
  },
  logo: { width: 180, height: 56 },
  card: {
    borderRadius: Radius.xl,
    borderWidth: StyleSheet.hairlineWidth,
    padding: Spacing.four,
    gap: Spacing.three,
  },
  alert: {
    borderRadius: Radius.sm,
    padding: Spacing.three,
  },
  forgot: {
    alignSelf: 'flex-start',
  },
  flexSpacer: { flex: 1, minHeight: Spacing.four },
  cta: {
    gap: Spacing.two,
  },
});
