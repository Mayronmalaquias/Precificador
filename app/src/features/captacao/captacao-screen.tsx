import { useCallback, useEffect, useMemo, useState } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { Button } from '@/components/ui/button';
import { ChipSelect, type ChipOption } from '@/components/ui/chip-select';
import { EmptyState } from '@/components/ui/empty-state';
import { Screen } from '@/components/ui/screen';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/components/ui/toast';
import { ThemedText } from '@/components/themed-text';
import { useSession } from '@/features/auth/session';
import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius, Spacing, Typography, shadow } from '@/theme';
import {
  listarCaptacoes,
  ETAPA_LABELS,
  type Captacao,
  type Etapa,
} from '@/features/captacao/api';
import { diasNaEtapa, statusMeta } from '@/features/captacao/helpers';
import { CreateCaptacaoModal } from '@/features/captacao/create-modal';
import { DetailCaptacaoModal } from '@/features/captacao/detail-modal';

type Filtro = 'todas' | Etapa;

export function CaptacaoScreen() {
  const { colors, isDark } = useAppTheme();
  const toast = useToast();
  const { user } = useSession();
  const idCorretor = useMemo(() => String(user?.id_usuarios || user?.id_corretor || ''), [user]);

  const [captacoes, setCaptacoes] = useState<Captacao[]>([]);
  const [loading, setLoading] = useState(!!idCorretor);
  const [refreshing, setRefreshing] = useState(false);
  const [filtro, setFiltro] = useState<Filtro>('todas');
  const [createOpen, setCreateOpen] = useState(false);
  const [selected, setSelected] = useState<Captacao | null>(null);

  // Carga inicial: IIFE async (sem setState síncrono no corpo do efeito).
  useEffect(() => {
    if (!idCorretor) return;
    let active = true;
    (async () => {
      try {
        const data = await listarCaptacoes(idCorretor);
        if (active) setCaptacoes(data);
      } catch (err: any) {
        if (active) toast.show({ type: 'error', message: err?.message || 'Erro ao carregar captações.' });
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [idCorretor, toast]);

  // Pull-to-refresh (handler de evento — pode setState de forma síncrona).
  const onRefresh = useCallback(async () => {
    if (!idCorretor) return;
    setRefreshing(true);
    try {
      setCaptacoes(await listarCaptacoes(idCorretor));
    } catch (err: any) {
      toast.show({ type: 'error', message: err?.message || 'Erro ao carregar captações.' });
    } finally {
      setRefreshing(false);
    }
  }, [idCorretor, toast]);

  const contagens = useMemo(() => {
    const map = new Map<Etapa, number>();
    for (const c of captacoes) map.set(c.etapa_atual, (map.get(c.etapa_atual) ?? 0) + 1);
    return map;
  }, [captacoes]);

  const filtros: ChipOption<Filtro>[] = useMemo(
    () => [
      { label: `Todas (${captacoes.length})`, value: 'todas' },
      ...(Object.keys(ETAPA_LABELS) as Etapa[]).map((e) => ({
        label: `${ETAPA_LABELS[e]} (${contagens.get(e) ?? 0})`,
        value: e as Filtro,
      })),
    ],
    [captacoes.length, contagens],
  );

  const lista = useMemo(
    () => (filtro === 'todas' ? captacoes : captacoes.filter((c) => c.etapa_atual === filtro)),
    [captacoes, filtro],
  );

  function handleCreated(c: Captacao) {
    setCaptacoes((prev) => [c, ...prev]);
    setCreateOpen(false);
  }

  function handleChanged(updated: Captacao | null) {
    if (!updated) {
      // excluída
      setCaptacoes((prev) => prev.filter((c) => c.id !== selected?.id));
      return;
    }
    setCaptacoes((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    setSelected(updated);
  }

  const header = (
    <View style={styles.headerBlock}>
      <View style={styles.titleRow}>
        <ThemedText style={[Typography.h1, { color: colors.text }]}>Captação</ThemedText>
        <Button
          label="Nova"
          icon="add"
          onPress={() => setCreateOpen(true)}
          fullWidth={false}
          size="md"
        />
      </View>
      <ChipSelect options={filtros} value={filtro} onChange={setFiltro} scroll />
    </View>
  );

  return (
    <Screen scroll={false} padded={false} edges={['top']}>
      {loading ? (
        <View style={styles.listContent}>
          {header}
          {[0, 1, 2].map((i) => (
            <View
              key={i}
              style={[styles.card, shadow('sm', isDark), { backgroundColor: colors.surface, borderColor: colors.border }]}>
              <Skeleton width="70%" height={16} />
              <Skeleton width="40%" height={12} />
            </View>
          ))}
        </View>
      ) : (
        <FlatList
          data={lista}
          keyExtractor={(item) => String(item.id)}
          ListHeaderComponent={header}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.brand} />}
          ListEmptyComponent={
            <View style={styles.empty}>
              <EmptyState
                icon="git-branch-outline"
                title={filtro === 'todas' ? 'Nenhuma captação' : 'Nada nesta etapa'}
                description={
                  filtro === 'todas'
                    ? 'Toque em “Nova” para lançar um imóvel na jornada.'
                    : 'Nenhum imóvel nesta etapa por enquanto.'
                }
              />
            </View>
          }
          renderItem={({ item }) => (
            <CaptacaoCard item={item} onPress={() => setSelected(item)} />
          )}
        />
      )}

      <CreateCaptacaoModal visible={createOpen} onClose={() => setCreateOpen(false)} onCreated={handleCreated} />
      {selected && (
        <DetailCaptacaoModal
          key={selected.id}
          captacao={selected}
          onClose={() => setSelected(null)}
          onChanged={handleChanged}
        />
      )}
    </Screen>
  );
}

function CaptacaoCard({ item, onPress }: { item: Captacao; onPress: () => void }) {
  const { colors, isDark } = useAppTheme();
  const meta = statusMeta(item.status, colors);
  const dias = diasNaEtapa(item.data_entrada_etapa);

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.card,
        shadow('sm', isDark),
        { backgroundColor: colors.surface, borderColor: colors.border, opacity: pressed ? 0.9 : 1 },
      ]}>
      <View style={styles.cardTop}>
        <ThemedText style={[Typography.bodyBold, { color: colors.text, flex: 1 }]} numberOfLines={1}>
          {item.endereco}
        </ThemedText>
        <View style={[styles.badge, { backgroundColor: meta.soft }]}>
          <ThemedText style={[Typography.caption, { color: meta.color }]}>{meta.label}</ThemedText>
        </View>
      </View>

      <ThemedText style={[Typography.caption, { color: colors.textSecondary }]} numberOfLines={1}>
        {item.bairro || 'Sem bairro'}
        {item.bloco ? ` · ${item.bloco}` : ''}
      </ThemedText>

      <View style={styles.cardBottom}>
        <View style={[styles.etapaPill, { backgroundColor: colors.brandSoft }]}>
          <Ionicons name="git-branch-outline" size={13} color={colors.brand} />
          <ThemedText style={[Typography.caption, { color: colors.brand }]}>
            {ETAPA_LABELS[item.etapa_atual]}
          </ThemedText>
        </View>
        {dias != null && (
          <ThemedText style={[Typography.caption, { color: colors.textMuted }]}>
            {dias} {dias === 1 ? 'dia' : 'dias'} na etapa
          </ThemedText>
        )}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  headerBlock: { gap: Spacing.three, paddingBottom: Spacing.two },
  titleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: Spacing.two },
  listContent: { padding: Spacing.four, gap: Spacing.three },
  card: {
    borderRadius: Radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    padding: Spacing.three,
    gap: Spacing.two,
  },
  cardTop: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  cardBottom: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: Spacing.two },
  badge: { paddingVertical: 3, paddingHorizontal: Spacing.two, borderRadius: Radius.pill },
  etapaPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.one,
    paddingVertical: 3,
    paddingHorizontal: Spacing.two,
    borderRadius: Radius.pill,
  },
  empty: { paddingVertical: Spacing.six },
});
