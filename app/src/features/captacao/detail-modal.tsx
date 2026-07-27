import { useEffect, useState } from 'react';
import { Platform, StyleSheet, View } from 'react-native';
import DateTimePicker, { type DateTimePickerEvent } from '@react-native-community/datetimepicker';
import { Ionicons } from '@expo/vector-icons';

import { Button } from '@/components/ui/button';
import { SectionCard } from '@/components/ui/section-card';
import { Skeleton } from '@/components/ui/skeleton';
import { TextField } from '@/components/ui/text-field';
import { ModalShell } from '@/components/ui/modal-shell';
import { useToast } from '@/components/ui/toast';
import { ThemedText } from '@/components/themed-text';
import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius, Spacing, Typography } from '@/theme';
import {
  atualizarCaptacao,
  etapaAnterior,
  excluirCaptacao,
  fecharCaptacao,
  listarHistorico,
  marcarExclusividade,
  proximaEtapa,
  ETAPAS,
  ETAPA_LABELS,
  type Captacao,
  type HistoricoItem,
} from '@/features/captacao/api';
import { diasNaEtapa, formatDateBR, statusMeta } from '@/features/captacao/helpers';
import { confirmAction } from '@/utils/confirm';

type Props = {
  captacao: Captacao;
  onClose: () => void;
  onChanged: (updated: Captacao | null) => void; // null = excluída
};

export function DetailCaptacaoModal({ captacao, onClose, onChanged }: Props) {
  const { colors } = useAppTheme();
  const toast = useToast();

  const [cap, setCap] = useState<Captacao>(captacao);
  const [historico, setHistorico] = useState<HistoricoItem[]>([]);
  const [loadingHist, setLoadingHist] = useState(true);
  const [busy, setBusy] = useState(false);

  const [showFechar, setShowFechar] = useState(false);
  const [motivo, setMotivo] = useState('');
  const [showDate, setShowDate] = useState(false);

  // Carrega histórico na montagem — o componente recebe key={id} do pai,
  // então remonta a cada captação (sem efeito de reset síncrono).
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const h = await listarHistorico(captacao.id);
        if (active) setHistorico(h);
      } catch {
        // mantém vazio
      } finally {
        if (active) setLoadingHist(false);
      }
    })();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fechado = cap.status === 'fechado';
  const meta = statusMeta(cap.status, colors);
  const idxAtual = ETAPAS.indexOf(cap.etapa_atual);
  const dias = diasNaEtapa(cap.data_entrada_etapa);

  async function refreshHist(id: number) {
    try {
      setHistorico(await listarHistorico(id));
    } catch {
      // mantém histórico anterior
    }
  }

  async function mutate(fn: () => Promise<Captacao>) {
    if (busy || !cap) return;
    setBusy(true);
    try {
      const updated = await fn();
      setCap(updated);
      onChanged(updated);
      await refreshHist(updated.id);
    } catch (err: any) {
      toast.show({ type: 'error', message: err?.message || 'Erro na operação.' });
    } finally {
      setBusy(false);
    }
  }

  function avancar() {
    const next = proximaEtapa(cap!.etapa_atual);
    if (!next) return;
    mutate(() => atualizarCaptacao(cap!.id, { etapa_atual: next }));
  }
  function voltar() {
    const prev = etapaAnterior(cap!.etapa_atual);
    if (!prev) return;
    mutate(() => atualizarCaptacao(cap!.id, { etapa_atual: prev }));
  }

  function onDate(event: DateTimePickerEvent, date?: Date) {
    if (Platform.OS === 'android') setShowDate(false);
    if (event.type === 'set' && date) {
      const iso = date.toISOString().split('T')[0];
      mutate(() => marcarExclusividade(cap!.id, iso));
    }
  }

  function confirmarFechar() {
    if (!motivo.trim()) {
      toast.show({ type: 'error', message: 'Informe o motivo do fechamento.' });
      return;
    }
    mutate(() => fecharCaptacao(cap!.id, motivo.trim())).then(() => setShowFechar(false));
  }

  function confirmarExcluir() {
    confirmAction({
      title: 'Excluir captação',
      message: 'Esta ação não pode ser desfeita. Continuar?',
      confirmLabel: 'Excluir',
      destructive: true,
      onConfirm: async () => {
        if (busy || !cap) return;
        setBusy(true);
        try {
          await excluirCaptacao(cap.id);
          toast.show({ type: 'success', message: 'Captação excluída.' });
          onChanged(null);
          onClose();
        } catch (err: any) {
          toast.show({ type: 'error', message: err?.message || 'Erro ao excluir.' });
        } finally {
          setBusy(false);
        }
      },
    });
  }

  const next = proximaEtapa(cap.etapa_atual);
  const prev = etapaAnterior(cap.etapa_atual);

  return (
    <ModalShell visible onClose={onClose} title={cap.endereco || 'Captação'}>
      {/* Resumo */}
      <SectionCard title="Resumo" icon="home-outline">
        <View style={styles.rowBetween}>
          <View style={[styles.badge, { backgroundColor: meta.soft }]}>
            <ThemedText style={[Typography.caption, { color: meta.color }]}>{meta.label}</ThemedText>
          </View>
          {dias != null && (
            <ThemedText style={[Typography.caption, { color: colors.textMuted }]}>
              {dias} {dias === 1 ? 'dia' : 'dias'} na etapa
            </ThemedText>
          )}
        </View>
        <InfoRow label="Bairro" value={cap.bairro || '—'} colors={colors} />
        {!!cap.bloco && <InfoRow label="Bloco" value={cap.bloco} colors={colors} />}
        {cap.status === 'exclusividade' && (
          <InfoRow label="Exclusividade até" value={formatDateBR(cap.exclusividade_ate)} colors={colors} />
        )}
        {fechado && <InfoRow label="Motivo" value={cap.motivo_fechamento || '—'} colors={colors} />}
      </SectionCard>

      {/* Etapas */}
      <SectionCard title="Etapa da jornada" icon="git-branch-outline">
        <View style={styles.stepper}>
          {ETAPAS.map((e, i) => {
            const done = i < idxAtual;
            const current = i === idxAtual;
            const bg = current ? colors.brand : done ? colors.brandSoft : colors.surfaceAlt;
            const fg = current ? colors.onBrand : done ? colors.brand : colors.textMuted;
            return (
              <View key={e} style={styles.step}>
                <View style={[styles.stepDot, { backgroundColor: bg, borderColor: current ? colors.brand : colors.border }]}>
                  {done ? (
                    <Ionicons name="checkmark" size={14} color={colors.brand} />
                  ) : (
                    <ThemedText style={[Typography.caption, { color: fg }]}>{i + 1}</ThemedText>
                  )}
                </View>
                <ThemedText
                  style={[Typography.caption, { color: current ? colors.text : colors.textMuted, textAlign: 'center' }]}
                  numberOfLines={1}>
                  {ETAPA_LABELS[e]}
                </ThemedText>
              </View>
            );
          })}
        </View>

        {!fechado && (
          <View style={styles.actionsRow}>
            <Button
              label="Voltar"
              variant="secondary"
              icon="arrow-back"
              onPress={voltar}
              disabled={busy || !prev}
              fullWidth={false}
              style={styles.flex1}
            />
            <Button
              label={next ? `Avançar: ${ETAPA_LABELS[next]}` : 'Última etapa'}
              icon="arrow-forward"
              onPress={avancar}
              disabled={busy || !next}
              fullWidth={false}
              style={styles.flex1}
            />
          </View>
        )}
      </SectionCard>

      {/* Ações */}
      {!fechado && (
        <SectionCard title="Ações" icon="options-outline">
          <Button
            label="Marcar exclusividade"
            variant="secondary"
            icon="ribbon-outline"
            onPress={() => setShowDate(true)}
            disabled={busy}
          />
          {showDate && (
            <DateTimePicker value={new Date()} mode="date" minimumDate={new Date()} onChange={onDate} />
          )}

          {showFechar ? (
            <View style={{ gap: Spacing.two }}>
              <TextField
                label="Motivo do fechamento"
                icon="close-circle-outline"
                placeholder="Ex: vendido por terceiros"
                value={motivo}
                onChangeText={setMotivo}
              />
              <View style={styles.actionsRow}>
                <Button label="Cancelar" variant="secondary" onPress={() => setShowFechar(false)} fullWidth={false} style={styles.flex1} />
                <Button label="Confirmar" variant="danger" onPress={confirmarFechar} loading={busy} fullWidth={false} style={styles.flex1} />
              </View>
            </View>
          ) : (
            <Button label="Fechar captação" variant="secondary" icon="lock-closed-outline" onPress={() => setShowFechar(true)} disabled={busy} />
          )}

          <Button label="Excluir" variant="danger" icon="trash-outline" onPress={confirmarExcluir} disabled={busy} />
        </SectionCard>
      )}

      {/* Histórico */}
      <SectionCard title="Histórico" icon="time-outline">
        {loadingHist ? (
          <View style={{ gap: Spacing.two }}>
            <Skeleton width="80%" height={14} />
            <Skeleton width="60%" height={14} />
            <Skeleton width="70%" height={14} />
          </View>
        ) : historico.length === 0 ? (
          <ThemedText style={[Typography.caption, { color: colors.textMuted }]}>
            Sem eventos ainda.
          </ThemedText>
        ) : (
          historico
            .slice()
            .reverse()
            .map((h) => (
              <View key={h.id} style={styles.histItem}>
                <View style={[styles.histDot, { backgroundColor: colors.brand }]} />
                <View style={{ flex: 1 }}>
                  <ThemedText style={[Typography.label, { color: colors.text }]}>{h.descricao}</ThemedText>
                  <ThemedText style={[Typography.caption, { color: colors.textMuted }]}>
                    {ETAPA_LABELS[h.etapa as keyof typeof ETAPA_LABELS] || h.etapa} · {formatDateBR(h.created_at)}
                  </ThemedText>
                </View>
              </View>
            ))
        )}
      </SectionCard>
    </ModalShell>
  );
}

function InfoRow({ label, value, colors }: { label: string; value: string; colors: ReturnType<typeof useAppTheme>['colors'] }) {
  return (
    <View style={styles.rowBetween}>
      <ThemedText style={[Typography.body, { color: colors.textSecondary }]}>{label}</ThemedText>
      <ThemedText style={[Typography.bodyBold, { color: colors.text, flex: 1, textAlign: 'right' }]} numberOfLines={1}>
        {value}
      </ThemedText>
    </View>
  );
}

const styles = StyleSheet.create({
  rowBetween: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: Spacing.two },
  badge: { alignSelf: 'flex-start', paddingVertical: 3, paddingHorizontal: Spacing.two, borderRadius: Radius.pill },
  stepper: { flexDirection: 'row', justifyContent: 'space-between', gap: 2 },
  step: { flex: 1, alignItems: 'center', gap: Spacing.one },
  stepDot: {
    width: 28,
    height: 28,
    borderRadius: Radius.pill,
    borderWidth: StyleSheet.hairlineWidth,
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionsRow: { flexDirection: 'row', gap: Spacing.two },
  flex1: { flex: 1 },
  histItem: { flexDirection: 'row', gap: Spacing.two, alignItems: 'flex-start' },
  histDot: { width: 8, height: 8, borderRadius: 4, marginTop: 6 },
});
