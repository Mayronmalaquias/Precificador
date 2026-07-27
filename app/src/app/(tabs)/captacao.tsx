import { LoginGate } from '@/components/ui/login-gate';
import { CaptacaoScreen } from '@/features/captacao/captacao-screen';
import { useSession } from '@/features/auth/session';

export default function CaptacaoTab() {
  const { isAuthenticated } = useSession();

  if (!isAuthenticated) {
    return <LoginGate description="Entre com sua conta 61 para ver suas captações." />;
  }

  return <CaptacaoScreen />;
}
