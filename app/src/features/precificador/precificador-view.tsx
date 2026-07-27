import { useCallback, useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { Button } from '@/components/ui/button';
import { ChipSelect, type ChipOption } from '@/components/ui/chip-select';
import { Screen } from '@/components/ui/screen';
import { Skeleton } from '@/components/ui/skeleton';
import { TextField } from '@/components/ui/text-field';
import { ThemedText } from '@/components/themed-text';
import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius, Spacing, Typography, shadow } from '@/theme';
import { formatBRL, formatM2, formatNumber, formatPercent } from '@/utils/format';
import {
  fetchPrecificacao,
  type MetricasAluguel,
  type MetricasVenda,
  type PrecificadorParams,
} from '@/features/precificador/api';

const BAIRROS: ChipOption[] = [
  { label: 'Asa Norte', value: 'ASA NORTE' },
  { label: 'Asa Sul', value: 'ASA SUL' },
  { label: 'Noroeste', value: 'NOROESTE' },
  { label: 'Sudoeste', value: 'SUDOESTE' },
  { label: 'Águas Claras', value: 'AGUAS CLARAS' },
];
const QUARTOS: ChipOption<number>[] = [
  { label: 'Todos', value: 0 },
  { label: '1', value: 1 },
  { label: '2', value: 2 },
  { label: '3', value: 3 },
  { label: '4+', value: 4 },
];
const VAGAS: ChipOption<number>[] = [
  { label: 'Todas', value: 10 },
  { label: '0', value: 0 },
  { label: '1+', value: 1 },
];
// Condição do imóvel → nrCluster (presets do Formulario.js web).
const CONDICAO: ChipOption<number>[] = [
  { label: 'Original', value: 1 },
  { label: 'Semi-reformado', value: 4 },
  { label: 'Reformado', value: 7 },
];

type Resultado = {
  venda: MetricasVenda | null;
  aluguel: MetricasAluguel | null;
  erroVenda: string | null;
  erroAluguel: string | null;
};

type Props = {
  /** Header opcional à direita (ex.: botão Entrar na home pública). */
  headerRight?: React.ReactNode;
};

export function PrecificadorView({ headerRight }: Props) {
  const { colors, isDark } = useAppTheme();

  const [tipoImovel] = useState('Apartamento');
  const [bairro, setBairro] = useState('ASA NORTE');
  const [quartos, setQuartos] = useState(0);
  const [vagas, setVagas] = useState(10);
  const [condicao, setCondicao] = useState(1);
  const [metragem, setMetragem] = useState('');

  const [result, setResult] = useState<Resultado | null>(null);
  const [loading, setLoading] = useState(true); // já carrega o estudo padrão no mount

  const buildParams = useCallback(
    (): PrecificadorParams => ({
      tipoImovel,
      bairro,
      quartos,
      vagas,
      nrCluster: condicao,
      metragem: parseInt(metragem || '0', 10) || 0,
    }),
    [tipoImovel, bairro, quartos, vagas, condicao, metragem],
  );

  const calcular = useCallback(async () => {
    setLoading(true);
    try {
      setResult(await fetchPrecificacao(buildParams()));
    } finally {
      setLoading(false);
    }
  }, [buildParams]);

  // Carrega o estudo padrão na montagem (mesmo comportamento do web).
  // Fetch dentro de IIFE async: nenhum setState síncrono no corpo do efeito.
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const data = await fetchPrecificacao(buildParams());
        if (active) setResult(data);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
    // Apenas na montagem — filtros disparam via botão Calcular.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const rentabilidade =
    result?.venda?.valorVendaNominal && result?.aluguel?.valorAluguelNominal
      ? (result.aluguel.valorAluguelNominal / result.venda.valorVendaNominal) * 100
      : null;

  return (
    <Screen scroll edges={['top']}>
      <View style={styles.headerRow}>
        <View style={{ flex: 1 }}>
          <ThemedText style={[Typography.h1, { color: colors.text }]}>Precificador</ThemedText>
          <ThemedText style={[Typography.caption, { color: colors.textSecondary }]}>
            Estimativa de venda e locação por região
          </ThemedText>
        </View>
        {headerRight}
      </View>

      {/* Filtros */}
      <View
        style={[
          styles.card,
          shadow('sm', isDark),
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}>
        <ChipSelect
          label="Tipo de imóvel"
          options={[{ label: 'Apartamento', value: 'Apartamento' }]}
          value={tipoImovel}
          onChange={() => {}}
        />
        <ChipSelect label="Bairro" options={BAIRROS} value={bairro} onChange={setBairro} scroll />
        <ChipSelect label="Quartos" options={QUARTOS} value={quartos} onChange={setQuartos} />
        <ChipSelect label="Vagas" options={VAGAS} value={vagas} onChange={setVagas} />
        <ChipSelect label="Condição" options={CONDICAO} value={condicao} onChange={setCondicao} scroll />

        <TextField
          label="Metragem (m²)"
          icon="resize-outline"
          placeholder="Opcional — usa a média da amostra"
          keyboardType="number-pad"
          value={metragem}
          onChangeText={(t) => setMetragem(t.replace(/[^0-9]/g, ''))}
          returnKeyType="done"
          onSubmitEditing={calcular}
        />

        <Button
          label="Calcular"
          icon="calculator-outline"
          onPress={calcular}
          loading={loading}
        />
      </View>

      {/* Resultado */}
      {loading && !result ? (
        <ResultSkeleton />
      ) : (
        result && (
          <>
            <MetricCard
              title="Venda"
              icon="pricetag-outline"
              highlightLabel="Valor de venda"
              highlightValue={formatBRL(result.venda?.valorVendaNominal)}
              error={result.venda ? null : result.erroVenda}
              rows={[
                { label: 'Valor do m²', value: `${formatBRL(result.venda?.valorM2Venda)} /m²` },
                { label: 'Metragem média', value: formatM2(result.venda?.metragemMediaVenda) },
                { label: 'Coef. de variação', value: formatPercent(result.venda?.coeficienteVariacaoVenda) },
                { label: 'Amostra', value: formatNumber(result.venda?.tamanhoAmostraVenda) },
              ]}
            />

            <MetricCard
              title="Locação"
              icon="home-outline"
              highlightLabel="Valor de locação"
              highlightValue={formatBRL(result.aluguel?.valorAluguelNominal)}
              error={result.aluguel ? null : result.erroAluguel}
              rows={[
                { label: 'Valor do m²', value: `${formatBRL(result.aluguel?.valorM2Aluguel)} /m²` },
                { label: 'Metragem média', value: formatM2(result.aluguel?.metragemMediaAluguel) },
                { label: 'Coef. de variação', value: formatPercent(result.aluguel?.coeficienteVariacaoAluguel) },
                { label: 'Amostra', value: formatNumber(result.aluguel?.tamanhoAmostraAluguel) },
              ]}
            />

            <View
              style={[
                styles.rentab,
                { backgroundColor: colors.brandSoft, borderColor: colors.brand + '33' },
              ]}>
              <Ionicons name="trending-up-outline" size={22} color={colors.brand} />
              <ThemedText style={[Typography.body, { color: colors.textSecondary, flex: 1 }]}>
                Rentabilidade média
              </ThemedText>
              <ThemedText style={[Typography.h2, { color: colors.brand }]}>
                {rentabilidade != null ? `${formatNumber(rentabilidade, 2)}%` : '—'}
              </ThemedText>
            </View>
          </>
        )
      )}
    </Screen>
  );
}

type MetricRow = { label: string; value: string };

function MetricCard({
  title,
  icon,
  highlightLabel,
  highlightValue,
  rows,
  error,
}: {
  title: string;
  icon: keyof typeof Ionicons.glyphMap;
  highlightLabel: string;
  highlightValue: string;
  rows: MetricRow[];
  error: string | null;
}) {
  const { colors, isDark } = useAppTheme();

  return (
    <View
      style={[
        styles.card,
        shadow('sm', isDark),
        { backgroundColor: colors.surface, borderColor: colors.border },
      ]}>
      <View style={styles.metricHeader}>
        <View style={[styles.metricIcon, { backgroundColor: colors.brandSoft }]}>
          <Ionicons name={icon} size={18} color={colors.brand} />
        </View>
        <ThemedText style={[Typography.title, { color: colors.text }]}>{title}</ThemedText>
      </View>

      {error ? (
        <View style={[styles.errorBox, { backgroundColor: colors.dangerSoft }]}>
          <Ionicons name="alert-circle-outline" size={18} color={colors.danger} />
          <ThemedText style={[Typography.caption, { color: colors.danger, flex: 1 }]}>
            {error}
          </ThemedText>
        </View>
      ) : (
        <>
          <View>
            <ThemedText style={[Typography.caption, { color: colors.textMuted }]}>
              {highlightLabel}
            </ThemedText>
            <ThemedText style={[Typography.display, { color: colors.text }]}>
              {highlightValue}
            </ThemedText>
          </View>

          <View style={[styles.divider, { backgroundColor: colors.border }]} />

          {rows.map((r) => (
            <View key={r.label} style={styles.metricRow}>
              <ThemedText style={[Typography.body, { color: colors.textSecondary }]}>
                {r.label}
              </ThemedText>
              <ThemedText style={[Typography.bodyBold, { color: colors.text }]}>
                {r.value}
              </ThemedText>
            </View>
          ))}
        </>
      )}
    </View>
  );
}

function ResultSkeleton() {
  const { colors, isDark } = useAppTheme();
  return (
    <View
      style={[
        styles.card,
        shadow('sm', isDark),
        { backgroundColor: colors.surface, borderColor: colors.border },
      ]}>
      <Skeleton width={120} height={18} />
      <Skeleton width={200} height={34} />
      <View style={[styles.divider, { backgroundColor: colors.border }]} />
      {[0, 1, 2, 3].map((i) => (
        <View key={i} style={styles.metricRow}>
          <Skeleton width={130} height={14} />
          <Skeleton width={80} height={14} />
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  headerRow: { flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.two },
  card: {
    borderRadius: Radius.xl,
    borderWidth: StyleSheet.hairlineWidth,
    padding: Spacing.four,
    gap: Spacing.three,
  },
  metricHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  metricIcon: {
    width: 32,
    height: 32,
    borderRadius: Radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  divider: { height: StyleSheet.hairlineWidth, marginVertical: Spacing.one },
  metricRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  errorBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    padding: Spacing.three,
    borderRadius: Radius.sm,
  },
  rentab: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.three,
    padding: Spacing.four,
    borderRadius: Radius.xl,
    borderWidth: StyleSheet.hairlineWidth,
  },
});
