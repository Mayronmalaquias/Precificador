import { useCallback, useEffect, useMemo, useState } from 'react';
import { FlatList, Linking, Pressable, RefreshControl, StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

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
  listarClientes,
  listarImoveis,
  listarVisitas,
  type ClienteItem,
  type ImovelItem,
  type VisitaItem,
} from '@/features/registros/api';
import { VisitaDetailModal } from '@/features/registros/visita-detail-modal';

type Seg = 'visitas' | 'clientes' | 'imoveis';

const WHATSAPP_GREEN = '#25D366';

/** Monta link wa.me. DDI 55 inferido por tamanho (não confunde com DDD 55/RS). */
function whatsappUrl(phone?: string): string | null {
  const d = String(phone || '').replace(/\D/g, '');
  if (d.length < 10) return null;
  const full = d.length >= 12 ? d : `55${d}`;
  return `https://wa.me/${full}`;
}

const SEGMENTOS: ChipOption<Seg>[] = [
  { label: 'Visitas', value: 'visitas' },
  { label: 'Clientes', value: 'clientes' },
  { label: 'Imóveis', value: 'imoveis' },
];

export function RegistrosScreen() {
  const { colors } = useAppTheme();
  const toast = useToast();
  const { user } = useSession();
  const idCorretor = useMemo(() => String(user?.id_usuarios || user?.id_corretor || ''), [user]);

  const [seg, setSeg] = useState<Seg>('visitas');
  const [visitas, setVisitas] = useState<VisitaItem[]>([]);
  const [clientes, setClientes] = useState<ClienteItem[]>([]);
  const [imoveis, setImoveis] = useState<ImovelItem[]>([]);
  const [loaded, setLoaded] = useState<Record<Seg, boolean>>({
    visitas: false,
    clientes: false,
    imoveis: false,
  });
  const [loading, setLoading] = useState(!!idCorretor);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedVisita, setSelectedVisita] = useState<VisitaItem | null>(null);

  const fetchSeg = useCallback(
    async (s: Seg) => {
      if (!idCorretor) return;
      if (s === 'visitas') setVisitas(await listarVisitas(idCorretor));
      else if (s === 'clientes') setClientes(await listarClientes(idCorretor));
      else setImoveis(await listarImoveis(idCorretor));
      setLoaded((prev) => ({ ...prev, [s]: true }));
    },
    [idCorretor],
  );

  // Carga inicial (Visitas) — IIFE async, sem setState síncrono no efeito.
  useEffect(() => {
    if (!idCorretor) return;
    let active = true;
    (async () => {
      try {
        await fetchSeg('visitas');
      } catch (err: any) {
        if (active) toast.show({ type: 'error', message: err?.message || 'Erro ao carregar.' });
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [idCorretor, fetchSeg, toast]);

  async function trocarSeg(s: Seg) {
    setSeg(s);
    if (loaded[s]) return;
    setLoading(true);
    try {
      await fetchSeg(s);
    } catch (err: any) {
      toast.show({ type: 'error', message: err?.message || 'Erro ao carregar.' });
    } finally {
      setLoading(false);
    }
  }

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await fetchSeg(seg);
    } catch (err: any) {
      toast.show({ type: 'error', message: err?.message || 'Erro ao carregar.' });
    } finally {
      setRefreshing(false);
    }
  }, [fetchSeg, seg, toast]);

  const lista: (VisitaItem | ClienteItem | ImovelItem)[] =
    seg === 'visitas' ? visitas : seg === 'clientes' ? clientes : imoveis;

  const header = (
    <View style={styles.headerBlock}>
      <ThemedText style={[Typography.h1, { color: colors.text }]}>Registros</ThemedText>
      <ChipSelect options={SEGMENTOS} value={seg} onChange={trocarSeg} />
    </View>
  );

  const emptyText: Record<Seg, { title: string; desc: string; icon: keyof typeof Ionicons.glyphMap }> = {
    visitas: { title: 'Sem visitas', desc: 'Suas visitas registradas aparecem aqui.', icon: 'clipboard-outline' },
    clientes: { title: 'Sem clientes', desc: 'Clientes das suas visitas aparecem aqui.', icon: 'people-outline' },
    imoveis: { title: 'Sem imóveis', desc: 'Imóveis no seu nome (captados por você) aparecem aqui.', icon: 'home-outline' },
  };

  return (
    <Screen scroll={false} padded={false} edges={['top']}>
      {loading && lista.length === 0 ? (
        <View style={styles.listContent}>
          {header}
          {[0, 1, 2].map((i) => (
            <View
              key={i}
              style={[styles.card, shadow('sm', false), { backgroundColor: colors.surface, borderColor: colors.border }]}>
              <Skeleton width="70%" height={16} />
              <Skeleton width="45%" height={12} />
            </View>
          ))}
        </View>
      ) : (
        <FlatList
          data={lista}
          keyExtractor={(item, index) =>
            seg === 'visitas'
              ? (item as VisitaItem).id_visita || String(index)
              : seg === 'clientes'
                ? String((item as ClienteItem).id_cliente ?? index)
                : String((item as ImovelItem).id_imovel || index)
          }
          ListHeaderComponent={header}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.brand} />}
          ListEmptyComponent={
            <View style={styles.empty}>
              <EmptyState icon={emptyText[seg].icon} title={emptyText[seg].title} description={emptyText[seg].desc} />
            </View>
          }
          renderItem={({ item }) => {
            if (seg === 'visitas') return <VisitaCard item={item as VisitaItem} onPress={() => setSelectedVisita(item as VisitaItem)} />;
            if (seg === 'clientes') return <ClienteCard item={item as ClienteItem} />;
            return <ImovelCard item={item as ImovelItem} />;
          }}
        />
      )}

      {selectedVisita && (
        <VisitaDetailModal
          key={selectedVisita.id_visita}
          visita={selectedVisita}
          onClose={() => setSelectedVisita(null)}
        />
      )}
    </Screen>
  );
}

function CardShell({ children, onPress }: { children: React.ReactNode; onPress?: () => void }) {
  const { colors, isDark } = useAppTheme();
  const style = [styles.card, shadow('sm', isDark), { backgroundColor: colors.surface, borderColor: colors.border }];
  if (!onPress) return <View style={style}>{children}</View>;
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [...style, { opacity: pressed ? 0.9 : 1 }]}>
      {children}
    </Pressable>
  );
}

function VisitaCard({ item, onPress }: { item: VisitaItem; onPress: () => void }) {
  const { colors } = useAppTheme();
  const naoCaptado = String(item.imovelNaoCaptado || '').toLowerCase() === 'sim' || !item.imovelId;
  const imovel = naoCaptado ? item.enderecoExterno || 'Não captado' : `Cod. ${item.imovelId}`;
  return (
    <CardShell onPress={onPress}>
      <View style={styles.rowTop}>
        <ThemedText style={[Typography.bodyBold, { color: colors.text, flex: 1 }]} numberOfLines={1}>
          {item.cliente || 'Cliente'}
        </ThemedText>
        {!!item.proposta && (
          <View style={[styles.badge, { backgroundColor: colors.brandSoft }]}>
            <ThemedText style={[Typography.caption, { color: colors.brand }]}>{item.proposta}</ThemedText>
          </View>
        )}
      </View>
      <ThemedText style={[Typography.caption, { color: colors.textSecondary }]} numberOfLines={1}>
        {imovel}
      </ThemedText>
      <View style={styles.rowBottom}>
        <Meta icon="calendar-outline" text={item.dataVisita || '—'} colors={colors} />
        <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
      </View>
    </CardShell>
  );
}

function ClienteCard({ item }: { item: ClienteItem }) {
  const { colors } = useAppTheme();
  const wa = whatsappUrl(item.telefone);
  return (
    <CardShell>
      <ThemedText style={[Typography.bodyBold, { color: colors.text }]} numberOfLines={1}>
        {item.nome || 'Cliente'}
      </ThemedText>
      <View style={styles.rowWrap}>
        {!!item.telefone && <Meta icon="call-outline" text={item.telefone} colors={colors} />}
        {!!item.email && <Meta icon="mail-outline" text={item.email} colors={colors} />}
        {!item.telefone && !item.email && (
          <ThemedText style={[Typography.caption, { color: colors.textMuted }]}>Sem contato</ThemedText>
        )}
      </View>
      {wa && (
        <Pressable
          onPress={() => Linking.openURL(wa)}
          accessibilityRole="button"
          accessibilityLabel="Abrir conversa no WhatsApp"
          style={({ pressed }) => [styles.waBtn, { backgroundColor: WHATSAPP_GREEN, opacity: pressed ? 0.85 : 1 }]}>
          <Ionicons name="logo-whatsapp" size={16} color="#FFFFFF" />
          <ThemedText style={[Typography.label, { color: '#FFFFFF' }]}>WhatsApp</ThemedText>
        </Pressable>
      )}
    </CardShell>
  );
}

function ImovelCard({ item }: { item: ImovelItem }) {
  const { colors } = useAppTheme();
  return (
    <CardShell>
      <ThemedText style={[Typography.bodyBold, { color: colors.text }]} numberOfLines={1}>
        {item.endereco_externo || (item.id_imovel ? `Cod. ${item.id_imovel}` : 'Imóvel')}
      </ThemedText>
      <View style={styles.rowWrap}>
        <Meta icon="clipboard-outline" text={`${item.qtd_visitas ?? 0} visita(s)`} colors={colors} />
        {!!item.ultima_data && <Meta icon="calendar-outline" text={`Última: ${item.ultima_data}`} colors={colors} />}
      </View>
      {!!item.clientes?.length && (
        <ThemedText style={[Typography.caption, { color: colors.textMuted }]} numberOfLines={1}>
          {item.clientes.join(', ')}
        </ThemedText>
      )}
    </CardShell>
  );
}

function Meta({ icon, text, colors }: { icon: keyof typeof Ionicons.glyphMap; text: string; colors: ReturnType<typeof useAppTheme>['colors'] }) {
  return (
    <View style={styles.meta}>
      <Ionicons name={icon} size={13} color={colors.textMuted} />
      <ThemedText style={[Typography.caption, { color: colors.textSecondary }]} numberOfLines={1}>
        {text}
      </ThemedText>
    </View>
  );
}

const styles = StyleSheet.create({
  headerBlock: { gap: Spacing.three, paddingBottom: Spacing.two },
  listContent: { padding: Spacing.four, gap: Spacing.three },
  card: {
    borderRadius: Radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    padding: Spacing.three,
    gap: Spacing.two,
  },
  rowTop: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  rowBottom: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  rowWrap: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: Spacing.three },
  badge: { paddingVertical: 3, paddingHorizontal: Spacing.two, borderRadius: Radius.pill },
  meta: { flexDirection: 'row', alignItems: 'center', gap: Spacing.one },
  empty: { paddingVertical: Spacing.six },
  waBtn: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.one,
    paddingVertical: Spacing.one + 2,
    paddingHorizontal: Spacing.three,
    borderRadius: Radius.pill,
    marginTop: Spacing.one,
  },
});
