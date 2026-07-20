import { Linking, StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui/button';
import { ModalShell } from '@/components/ui/modal-shell';
import { SectionCard } from '@/components/ui/section-card';
import { ThemedText } from '@/components/themed-text';
import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius, Spacing, Typography } from '@/theme';
import type { VisitaItem } from '@/features/registros/api';

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

type Props = { visita: VisitaItem; onClose: () => void };

export function VisitaDetailModal({ visita, onClose }: Props) {
  const { colors } = useAppTheme();

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
