import type { ReactNode } from 'react';
import {
  KeyboardAvoidingView,
  ScrollView,
  StyleSheet,
  View,
  type ViewStyle,
} from 'react-native';
import { SafeAreaView, type Edge } from 'react-native-safe-area-context';

import { useAppTheme } from '@/hooks/use-app-theme';
import { Spacing } from '@/theme';

/**
 * Quanto o conteudo sobe ALEM da altura do teclado.
 *
 * Levantar exatamente o teclado deixa o campo focado encostado nele, e o que vem logo
 * abaixo na ordem da tela (rotulo de erro, "Esqueceu a senha?", o botao de acao) fica
 * escondido — o teclado nao e o unico componente que precisa caber. O RN desconta este
 * valor do topo do teclado antes de medir a sobreposicao, entao ele vira folga real:
 *
 *   keyboardY = topo_do_teclado - keyboardVerticalOffset   (KeyboardAvoidingView.js)
 *
 * `Spacing.six` cobre uma linha de campo inteira com respiro. Telas com rodape mais alto
 * passam o proprio valor por `keyboardOffset`.
 */
export const FOLGA_TECLADO = Spacing.six;

type Props = {
  children: ReactNode;
  scroll?: boolean;
  /** Envolve em KeyboardAvoidingView (telas com formulário). */
  keyboardAvoiding?: boolean;
  /** Folga acima do teclado, em px. Ver `FOLGA_TECLADO`. */
  keyboardOffset?: number;
  edges?: readonly Edge[];
  contentStyle?: ViewStyle;
  padded?: boolean;
};

export function Screen({
  children,
  scroll = false,
  keyboardAvoiding = false,
  keyboardOffset = FOLGA_TECLADO,
  edges = ['top', 'bottom'],
  contentStyle,
  padded = true,
}: Props) {
  const { colors } = useAppTheme();

  const inner = scroll ? (
    <ScrollView
      style={styles.flex}
      contentContainerStyle={[padded && styles.padded, contentStyle]}
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}>
      {children}
    </ScrollView>
  ) : (
    <View style={[styles.flex, padded && styles.padded, contentStyle]}>{children}</View>
  );

  // `behavior` indefinido faz o KeyboardAvoidingView cair no `default` e renderizar uma
  // View crua — no Android ele virava no-op. Antes isso passava porque a janela encolhia
  // sozinha (adjustResize); com o edge-to-edge padrao do SDK 54+ ela nao encolhe mais, e o
  // teclado cobria o campo focado. `padding` nao duplica espaco quando a janela TAMBEM
  // encolhe: o RN mede o proprio frame contra o topo do teclado e devolve 0 se ja estiver
  // acima dele.
  const body = keyboardAvoiding ? (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior="padding"
      keyboardVerticalOffset={keyboardOffset}>
      {inner}
    </KeyboardAvoidingView>
  ) : (
    inner
  );

  return (
    <SafeAreaView edges={edges} style={[styles.flex, { backgroundColor: colors.canvas }]}>
      {body}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  padded: {
    padding: Spacing.four,
    gap: Spacing.three,
  },
});
