import { useMemo, useState } from 'react';
import { View } from 'react-native';

import { Button } from '@/components/ui/button';
import { ChipSelect } from '@/components/ui/chip-select';
import { ModalShell } from '@/components/ui/modal-shell';
import { TextField } from '@/components/ui/text-field';
import { useToast } from '@/components/ui/toast';
import { useSession } from '@/features/auth/session';
import { Spacing } from '@/theme';
import { criarCaptacao, type Captacao } from '@/features/captacao/api';

type Props = {
  visible: boolean;
  onClose: () => void;
  onCreated: (c: Captacao) => void;
};

export function CreateCaptacaoModal({ visible, onClose, onCreated }: Props) {
  const toast = useToast();
  const { user, nomeUsuario } = useSession();

  const idCorretor = useMemo(
    () => String(user?.id_usuarios || user?.id_corretor || ''),
    [user],
  );

  const [endereco, setEndereco] = useState('');
  const [bairro, setBairro] = useState('');
  const [bloco, setBloco] = useState('');
  const [numero, setNumero] = useState('');
  const [temNumero, setTemNumero] = useState<'sim' | 'nao' | ''>('');
  const [link, setLink] = useState('');
  const [loading, setLoading] = useState(false);

  function reset() {
    setEndereco('');
    setBairro('');
    setBloco('');
    setNumero('');
    setTemNumero('');
    setLink('');
  }

  async function salvar() {
    if (loading) return;
    if (!endereco.trim()) {
      toast.show({ type: 'error', message: 'Informe o endereço do imóvel.' });
      return;
    }
    if (!idCorretor) {
      toast.show({ type: 'error', message: 'Sessão inválida. Entre novamente.' });
      return;
    }
    setLoading(true);
    try {
      const c = await criarCaptacao({
        id_corretor: idCorretor,
        nome_corretor: nomeUsuario,
        team: String(user?.team || '') || undefined,
        endereco: endereco.trim(),
        bairro: bairro.trim() || undefined,
        bloco: bloco.trim() || undefined,
        numero_imovel: numero.trim() || undefined,
        tem_numero: temNumero === 'sim' ? true : temNumero === 'nao' ? false : undefined,
        link_anuncio: link.trim() || undefined,
        etapa_atual: 'escolha',
      });
      toast.show({ type: 'success', message: 'Captação criada!' });
      reset();
      onCreated(c);
    } catch (err: any) {
      toast.show({ type: 'error', message: err?.message || 'Erro ao criar captação.' });
    } finally {
      setLoading(false);
    }
  }

  return (
    <ModalShell
      visible={visible}
      onClose={onClose}
      title="Nova captação"
      footer={
        <Button
          label={loading ? 'Salvando...' : 'Criar captação'}
          icon={loading ? undefined : 'add'}
          onPress={salvar}
          loading={loading}
        />
      }>
      <View style={{ gap: Spacing.three }}>
        <TextField
          label="Endereço"
          icon="location-outline"
          placeholder="Ex: SQS 308 Bloco B Apt 204"
          value={endereco}
          onChangeText={setEndereco}
        />
        <TextField label="Bairro" icon="map-outline" placeholder="Ex: Asa Sul" value={bairro} onChangeText={setBairro} />
        <TextField label="Bloco" icon="business-outline" placeholder="Opcional" value={bloco} onChangeText={setBloco} />
        <TextField
          label="Número do imóvel"
          icon="pricetag-outline"
          placeholder="Opcional"
          value={numero}
          onChangeText={setNumero}
        />
        <ChipSelect
          label="Tem número?"
          options={[
            { label: 'Sim', value: 'sim' },
            { label: 'Não', value: 'nao' },
          ]}
          value={temNumero}
          onChange={(v) => setTemNumero((prev) => (prev === v ? '' : (v as 'sim' | 'nao')))}
        />
        <TextField
          label="Link do anúncio (opcional)"
          icon="link-outline"
          placeholder="https://..."
          autoCapitalize="none"
          value={link}
          onChangeText={setLink}
        />
      </View>
    </ModalShell>
  );
}
