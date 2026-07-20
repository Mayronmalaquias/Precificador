import { LoginGate } from '@/components/ui/login-gate';
import { VisitaForm } from '@/features/visita/visita-form';
import { useSession } from '@/features/auth/session';

export default function VisitaScreen() {
  const { isAuthenticated } = useSession();

  if (!isAuthenticated) {
    return <LoginGate description="Entre com sua conta 61 para registrar visitas." />;
  }

  return <VisitaForm />;
}
