import { LoginGate } from '@/components/ui/login-gate';
import { RegistrosScreen } from '@/features/registros/registros-screen';
import { useSession } from '@/features/auth/session';

export default function RegistrosTab() {
  const { isAuthenticated } = useSession();

  if (!isAuthenticated) {
    return <LoginGate description="Entre com sua conta 61 para ver seus registros." />;
  }

  return <RegistrosScreen />;
}
