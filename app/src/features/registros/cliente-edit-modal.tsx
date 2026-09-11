import { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui/button';
import { ModalShell } from '@/components/ui/modal-shell';
import { SectionCard } from '@/components/ui/section-card';
import { Skeleton } from '@/components/ui/skeleton';
import { TextField } from '@/components/ui/text-field';
import { useToast } from '@/components/ui/toast';
import { ThemedText } from '@/components/themed-text';
import { useAppTheme } from '@/hooks/use-app-theme';
import { Spacing, Typography } from '@/theme';
import {
  editarCliente,
  obterCliente,
  type ClienteDetalhe,
  type ClienteItem,
} from '@/features/registros/api';

type Props = {
  cliente: ClienteItem;
  solicitanteId: string;
  onClose: () => void;
  onSaved: (c: ClienteDetalhe) => void;
};

/**
 * Edita nome, telefone e e-mail. Abre buscando o cadastro em vez de confiar no
 * item da lista: `/clientes_busca` devolve o que a busca tem em cache, e é o
 * GET que confirma se o cliente ainda está no escopo de quem abriu.
 */
export function ClienteEditModal({ cliente, solicitanteId, onClose, onSaved }: Props) {
  const { colors } = useAppTheme();
  const toast = useToast();

  const id = String(cliente.id_cliente ?? '');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [erro, setErro] = useState('');
  const [original, setOriginal] = useState<ClienteDetalhe | null>(null);

  const [nome, setNome] = useState(String(cliente.nome ?? ''));
  const [telefone, setTelefone] = useState(String(cliente.telefone ?? ''));
  const [email, setEmail] = useState(String(cliente.email ?? ''));

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const c = await obterCliente(id, solicitanteId);
        if (!active) return;
        if (c) {
          setOriginal(c);
          setNome(c.nome);
          setTelefone(c.telefone);
          setEmail(c.email);
        }
      } catch (err: any) {
        if (active) setErro(err?.message || 'Não foi possível abrir o cliente.');
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function salvar() {
    if (busy) return;
    if (!nome.trim()) {
      toast.show({ type: 'error', message: 'O nome não pode ficar vazio.' });
      return;
    }

    // Só o que mudou: chave ausente mantém o valor, chave vazia apaga.
    const base = original ?? { nome: cliente.nome ?? '', telefone: cliente.telefone ?? '', email: cliente.email ?? '' };
    const campos: Record<string, string> = {};
    if (nome.trim() !== String(base.nome ?? '')) campos.nome = nome.trim();
    if (telefone.trim() !== String(base.telefone ?? '')) campos.telefone = telefone.trim();
    if (email.trim() !== String(base.email ?? '')) campos.email = email.trim();

    if (Object.keys(campos).length === 0) {
      toast.show({ type: 'info', message: 'Nada mudou.' });
      onClose();
      return;
    }

    setBusy(true);
    try {
      const atualizado = await editarCliente(id, solicitanteId, campos);
      toast.show({ type: 'success', message: 'Cliente atualizado.' });
      onSaved(atualizado);
      onClose();
    } catch (err: any) {
      toast.show({ type: 'error', message: err?.message || 'Erro ao salvar.' });
    } finally {
      setBusy(false);
    }
  }

  return (
    <ModalShell visible onClose={onClose} title={cliente.nome || 'Cliente'}>
      <SectionCard title="Contato" icon="person-outline">
        {loading ? (
          <View style={{ gap: Spacing.two }}>
            <Skeleton width="100%" height={44} />
            <Skeleton width="100%" height={44} />
            <Skeleton width="100%" height={44} />
          </View>
        ) : erro ? (
          <ThemedText style={[Typography.body, { color: colors.danger }]}>{erro}</ThemedText>
        ) : (
          <View style={{ gap: Spacing.two }}>
            <TextField label="Nome" icon="person-outline" value={nome} onChangeText={setNome} />
            <TextField
              label="Telefone"
              icon="call-outline"
              keyboardType="phone-pad"
              value={telefone}
              onChangeText={setTelefone}
            />
            <TextField
              label="E-mail"
              icon="mail-outline"
              keyboardType="email-address"
              autoCapitalize="none"
              value={email}
              onChangeText={setEmail}
            />
            <View style={styles.actionsRow}>
              <Button label="Cancelar" variant="secondary" onPress={onClose} fullWidth={false} style={styles.flex1} />
              <Button label="Salvar" icon="save-outline" onPress={salvar} loading={busy} fullWidth={false} style={styles.flex1} />
            </View>
          </View>
        )}
      </SectionCard>
    </ModalShell>
  );
}

const styles = StyleSheet.create({
  actionsRow: { flexDirection: 'row', gap: Spacing.two },
  flex1: { flex: 1 },
});
