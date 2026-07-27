import { View } from 'react-native';
import { useRouter } from 'expo-router';

import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Screen } from '@/components/ui/screen';
import { Spacing } from '@/theme';

type Props = {
  title?: string;
  description?: string;
};

/** Barreira amigável para telas de corretor quando o usuário não está logado. */
export function LoginGate({
  title = 'Acesso restrito',
  description = 'Entre com sua conta 61 para acessar esta área.',
}: Props) {
  const router = useRouter();
  return (
    <Screen edges={['top']}>
      <View style={{ flex: 1 }}>
        <EmptyState icon="lock-closed-outline" title={title} description={description} />
      </View>
      <View style={{ paddingBottom: Spacing.two }}>
        <Button label="Entrar" icon="log-in-outline" onPress={() => router.push('/login')} />
      </View>
    </Screen>
  );
}
