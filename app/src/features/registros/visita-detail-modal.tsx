import { useEffect, useState } from 'react';
import { Linking, StyleSheet, View } from 'react-native';

import { Ionicons } from '@expo/vector-icons';

import { Button } from '@/components/ui/button';
import { ModalShell } from '@/components/ui/modal-shell';
import { SectionCard } from '@/components/ui/section-card';
import { ThemedText } from '@/components/themed-text';
import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius, Spacing, Typography } from '@/theme';
import { obterVisita, type VisitaDetalhe, type VisitaItem } from '@/features/registros/api';

const NOTA_LABELS: { key: keyof NotaKeys; label: string }[] = [
  { key: 'localizacao', label: 'Localização' },
  { key: 'tamanho', label: 'Tamanho' },
  { key: 'planta', label: 'Planta' },
  { key: 'acabamento', label: 'Acabamento' },
  { key: 'conservacao', label: 'Conservação' },
  { key: 'condominio', label: 'Condomínio' },
  { key: 'preco', label: 'Preço' },
  { key: 'notaGeral', label: 'Nota geral' },
];
type NotaKeys = {
  localizacao?: string;
  tamanho?: string;
  planta?: string;
  acabamento?: string;
  conservacao?: string;
  condominio?: string;
  preco?: string;
  notaGeral?: string;
};

type Props = { visita: VisitaItem; solicitanteId: string; onClose: () => void };

/** Rótulo de cada pendência devolvida por `GET /visitas/{id}`. */
const PENDENCIA_LABELS: Record<string, string> = {
  anexo: 'Anexo não revisado',
  notas: 'Notas não revisadas',
  motivo: 'Motivo da resposta em aberto',
};

export function VisitaDetailModal({ visita, solicitanteId, onClose }: Props) {
  const { colors } = useAppTheme();

  // Enriquecimento: `/visitas_busca` não traz resposta do cliente nem pendência
  // de revisão. Falha em silêncio — o modal já renderiza sem isso.
  const [detalhe, setDetalhe] = useState<VisitaDetalhe | null>(null);
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const d = await obterVisita(visita.id_visita, solicitanteId);
        if (active) setDetalhe(d);
      } catch {
        // segue com o que veio da lista
      }
    })();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const clientePrincipal = visita.clientes?.[0];
  const naoCaptado = String(visita.imovelNaoCaptado || '').toLowerCase() === 'sim' || !visita.imovelId;
  const aval = visita.avaliacoes?.[0];
  const anexo = visita.linkImagem || visita.anexoFichaVisita;

  return (
    <ModalShell visible onClose={onClose} title={`Visita ${visita.id_visita}`}>
      <SectionCard title="Cliente" icon="person-outline">
        <InfoRow label="Nome" value={visita.cliente || clientePrincipal?.nome || '—'} colors={colors} />
        {!!clientePrincipal?.telefone && <InfoRow label="Telefone" value={clientePrincipal.telefone} colors={colors} />}
        {!!clientePrincipal?.email && <InfoRow label="E-mail" value={clientePrincipal.email} colors={colors} />}
      </SectionCard>

      <SectionCard title="Imóvel & visita" icon="home-outline">
        <InfoRow
          label="Imóvel"
          value={naoCaptado ? visita.enderecoExterno || 'Não captado' : `Cod. ${visita.imovelId}`}
          colors={colors}
        />
        {!naoCaptado && !!visita.enderecoExterno && (
          <InfoRow label="Endereço" value={visita.enderecoExterno} colors={colors} />
        )}
        <InfoRow label="Data" value={visita.dataVisita || '—'} colors={colors} />
        <InfoRow label="Proposta" value={visita.proposta || '—'} colors={colors} />
        {!!visita.tipoCaptacao && <InfoRow label="Captação" value={visita.tipoCaptacao} colors={colors} />}
      </SectionCard>

      {aval && (
        <SectionCard title="Avaliações" icon="star-outline">
          {NOTA_LABELS.map(({ key, label }) => (
            <View key={key} style={styles.notaRow}>
              <ThemedText style={[Typography.body, { color: colors.textSecondary }]}>{label}</ThemedText>
              <View style={[styles.notaPill, { backgroundColor: colors.brandSoft }]}>
                <ThemedText style={[Typography.label, { color: colors.brand }]}>
                  {aval[key] ?? '—'}
                </ThemedText>
              </View>
            </View>
          ))}
        </SectionCard>
      )}

      {!!detalhe && (!!detalhe.motivo_sim || !!detalhe.motivo_talvez) && (
        <SectionCard title="Resposta do cliente" icon="chatbubble-ellipses-outline">
          {!!detalhe.motivo_sim && <InfoRow label="Motivo (sim)" value={detalhe.motivo_sim} colors={colors} />}
          {!!detalhe.motivo_talvez && <InfoRow label="Motivo (talvez)" value={detalhe.motivo_talvez} colors={colors} />}
        </SectionCard>
      )}

      {!!detalhe?.revisao_pendente && (
        <SectionCard title="Revisão do gerente" icon="alert-circle-outline">
          {(detalhe.pendencias ?? []).map((p) => (
            <View key={p} style={styles.infoRow}>
              <Ionicons name="ellipse" size={8} color={colors.danger} />
              <ThemedText style={[Typography.body, { color: colors.text, flex: 1 }]}>
                {PENDENCIA_LABELS[p] ?? p}
              </ThemedText>
            </View>
          ))}
        </SectionCard>
      )}

      {!!anexo && (
        <SectionCard title="Ficha anexada" icon="document-attach-outline">
          <Button
            label="Abrir anexo"
            variant="secondary"
            icon="open-outline"
            onPress={() => Linking.openURL(anexo)}
          />
        </SectionCard>
      )}
    </ModalShell>
  );
}

function InfoRow({ label, value, colors }: { label: string; value: string; colors: ReturnType<typeof useAppTheme>['colors'] }) {
  return (
    <View style={styles.infoRow}>
      <ThemedText style={[Typography.body, { color: colors.textSecondary }]}>{label}</ThemedText>
      <ThemedText style={[Typography.bodyBold, { color: colors.text, flex: 1, textAlign: 'right' }]} numberOfLines={2}>
        {value}
      </ThemedText>
    </View>
  );
}

const styles = StyleSheet.create({
  infoRow: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: Spacing.three },
  notaRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  notaPill: { minWidth: 40, alignItems: 'center', paddingVertical: 3, paddingHorizontal: Spacing.two, borderRadius: Radius.pill },
});
