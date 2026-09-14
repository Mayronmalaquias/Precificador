import type { ReactNode } from 'react';
import {
  KeyboardAvoidingView,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius, Spacing, Typography } from '@/theme';
import { ThemedText } from '@/components/themed-text';
import { FOLGA_TECLADO } from '@/components/ui/screen';

type Props = {
  visible: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  /** Folga acima do teclado, em px. Ver `FOLGA_TECLADO`. */
  keyboardOffset?: number;
};

/** Modal em tela cheia com cabeçalho + corpo rolável e rodapé fixo opcional. */
export function ModalShell({
  visible,
  onClose,
  title,
  children,
  footer,
  keyboardOffset = FOLGA_TECLADO,
}: Props) {
  const { colors } = useAppTheme();

  return (
    <Modal visible={visible} onRequestClose={onClose} animationType="slide" transparent={false}>
      {/* O `Modal` do react-native monta uma raiz nativa PROPRIA, fora da view que o
          SafeAreaProvider do app mede. Sem um provider aqui dentro, o `SafeAreaView`
          abaixo herdava inset do contexto da raiz e o cabecalho subia para debaixo da
          status bar / Dynamic Island — o X ficava em cima dos indicadores do iPhone.
          Provider aninhado e o caminho previsto pela lib: ele mede a raiz do modal e,
          enquanto mede, cai nos insets do pai em vez de piscar com zero. */}
      <SafeAreaProvider>
        <SafeAreaView style={[styles.flex, { backgroundColor: colors.canvas }]} edges={['top', 'bottom']}>
          <View style={[styles.header, { borderBottomColor: colors.border }]}>
            <ThemedText style={[Typography.title, { flex: 1 }]} numberOfLines={1}>
              {title}
            </ThemedText>
            <Pressable
              onPress={onClose}
              hitSlop={12}
              accessibilityRole="button"
              accessibilityLabel="Fechar"
              style={[styles.close, { backgroundColor: colors.surfaceAlt }]}>
              <Ionicons name="close" size={20} color={colors.textSecondary} />
            </Pressable>
          </View>

          {/* `padding` nos dois: sem `behavior` o componente e no-op no Android, e desde o
              edge-to-edge do SDK 54+ a janela nao encolhe mais sozinha com o teclado. O
              offset sobe o corpo alem do teclado para o rodape fixo nao comer o campo. */}
          <KeyboardAvoidingView
            style={styles.flex}
            behavior="padding"
            keyboardVerticalOffset={keyboardOffset}>
            <ScrollView
              contentContainerStyle={styles.body}
              keyboardShouldPersistTaps="handled"
              showsVerticalScrollIndicator={false}>
              {children}
            </ScrollView>
            {footer && (
              <View style={[styles.footer, { borderTopColor: colors.border, backgroundColor: colors.canvas }]}>
                {footer}
              </View>
            )}
          </KeyboardAvoidingView>
        </SafeAreaView>
      </SafeAreaProvider>
    </Modal>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    paddingHorizontal: Spacing.four,
    paddingVertical: Spacing.three,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  close: {
    width: 36,
    height: 36,
    borderRadius: Radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  body: {
    padding: Spacing.four,
    gap: Spacing.three,
  },
  footer: {
    padding: Spacing.four,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
});
