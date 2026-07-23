import { useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { Button } from '@/components/ui/button';
import { Screen } from '@/components/ui/screen';
import { TextField } from '@/components/ui/text-field';
import { ThemedText } from '@/components/themed-text';
import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius, Spacing, Typography, shadow } from '@/theme';
import { formatBRL } from '@/utils/format';

/** Formata o texto digitado como moeda BRL (centavos → R$). */
function formatarMoedaInput(valor: string): string {
  const somenteNumeros = valor.replace(/\D/g, '');
  if (!somenteNumeros) return '';
  const numero = Number(somenteNumeros) / 100;
  return numero.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

/** Converte a string mascarada de volta para número. */
function converterMoedaParaNumero(valor: string): number {
  if (!valor) return 0;
  return (
    Number(
      valor
        .replace(/\s/g, '')
        .replace('R$', '')
        .replace(/\./g, '')
        .replace(',', '.'),
    ) || 0
  );
}

type Props = {
  /** Header opcional à direita (ex.: botão Entrar na home pública). */
  headerRight?: React.ReactNode;
};

export function FinanciamentoView({ headerRight }: Props) {
  const { colors, isDark } = useAppTheme();

  const [precoImovel, setPrecoImovel] = useState('');
  const [valorDinheiro, setValorDinheiro] = useState('');

  const resultados = useMemo(() => {
    const preco = converterMoedaParaNumero(precoImovel);
    const dinheiro = converterMoedaParaNumero(valorDinheiro);

    const valorFinanciamento = Math.max(preco - dinheiro, 0);
    const prestacaoEstimada = valorFinanciamento * 0.0125;
    const rendaNecessaria = prestacaoEstimada / 0.3;

    return { valorFinanciamento, prestacaoEstimada, rendaNecessaria };
  }, [precoImovel, valorDinheiro]);

  const limpar = () => {
    setPrecoImovel('');
    setValorDinheiro('');
  };

  return (
    <Screen scroll keyboardAvoiding>
      {/* Header */}
      <View style={styles.header}>
        <View style={{ flex: 1 }}>
          <ThemedText style={[Typography.h1, { color: colors.text }]}>61 Financeiro</ThemedText>
          <ThemedText style={[Typography.caption, { color: colors.textSecondary }]}>
            Simulação de financiamento e capacidade estimada de compra
          </ThemedText>
        </View>
        {headerRight}
      </View>

      {/* Tutorial */}
      <View
        style={[
          styles.tutorial,
          { backgroundColor: colors.brandSoft, borderColor: colors.brand + '33' },
        ]}>
        <View style={styles.tutorialHead}>
          <Ionicons name="bulb-outline" size={18} color={colors.brand} />
          <ThemedText style={[Typography.label, { color: colors.brand }]}>
            Como usar
          </ThemedText>
        </View>
        <ThemedText style={[Typography.caption, { color: colors.textSecondary }]}>
          1. Informe o preço do imóvel.{'\n'}
          2. Informe o valor em dinheiro do cliente.{'\n'}
          3. O sistema calcula o valor a financiar, a 1ª parcela estimada e a renda necessária.{'\n'}
          Cálculo estimativo — apoio comercial inicial.
        </ThemedText>
      </View>

      {/* Formulário */}
      <View
        style={[
          styles.card,
          shadow('sm', isDark),
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}>
        <TextField
          label="Preço do imóvel"
          icon="home-outline"
          placeholder="R$ 0,00"
          keyboardType="number-pad"
          value={precoImovel}
          onChangeText={(t) => setPrecoImovel(formatarMoedaInput(t))}
        />
        <TextField
          label="Valor em dinheiro"
          icon="cash-outline"
          placeholder="R$ 0,00"
          keyboardType="number-pad"
          value={valorDinheiro}
          onChangeText={(t) => setValorDinheiro(formatarMoedaInput(t))}
        />
        <Button label="Limpar" variant="secondary" icon="refresh-outline" onPress={limpar} />
      </View>

      {/* Resultado */}
      <View
        style={[
          styles.destaque,
          shadow('md', isDark),
          { backgroundColor: colors.brand },
        ]}>
        <ThemedText style={[Typography.caption, { color: colors.onBrand, opacity: 0.85 }]}>
          Valor do financiamento
        </ThemedText>
        <ThemedText style={[Typography.display, { color: colors.onBrand }]}>
          {formatBRL(resultados.valorFinanciamento)}
        </ThemedText>
        <ThemedText style={[Typography.caption, { color: colors.onBrand, opacity: 0.85 }]}>
          Preço do imóvel − valor em dinheiro
        </ThemedText>
      </View>

      <View style={styles.grid}>
        <ResultCard
          label="1ª parcela estimada"
          value={formatBRL(resultados.prestacaoEstimada)}
          hint="Prazo 420 meses"
        />
        <ResultCard
          label="Renda necessária"
          value={formatBRL(resultados.rendaNecessaria)}
          hint="Parcela ≤ 30% da renda"
        />
      </View>
    </Screen>
  );
}

function ResultCard({ label, value, hint }: { label: string; value: string; hint: string }) {
  const { colors, isDark } = useAppTheme();
  return (
    <View
      style={[
        styles.resultCard,
        shadow('sm', isDark),
        { backgroundColor: colors.surface, borderColor: colors.border },
      ]}>
      <ThemedText style={[Typography.caption, { color: colors.textSecondary }]}>{label}</ThemedText>
      <ThemedText style={[Typography.h2, { color: colors.text }]}>{value}</ThemedText>
      <ThemedText style={[Typography.caption, { color: colors.textMuted }]}>{hint}</ThemedText>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
  },
  tutorial: {
    borderRadius: Radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    padding: Spacing.four,
    gap: Spacing.two,
  },
  tutorialHead: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  card: {
    borderRadius: Radius.xl,
    borderWidth: StyleSheet.hairlineWidth,
    padding: Spacing.four,
    gap: Spacing.three,
  },
  destaque: {
    borderRadius: Radius.xl,
    padding: Spacing.four,
    gap: Spacing.one,
  },
  grid: {
    flexDirection: 'row',
    gap: Spacing.three,
  },
  resultCard: {
    flex: 1,
    borderRadius: Radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    padding: Spacing.four,
    gap: Spacing.one,
  },
});
