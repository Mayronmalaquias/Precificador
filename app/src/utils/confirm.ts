import { Alert, Platform } from 'react-native';

type ConfirmOptions = {
  title: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm: () => void;
};

/**
 * Confirmação cross-platform.
 * Web: Alert.alert do react-native-web não dispara callbacks de botão — usa window.confirm.
 * Nativo: Alert.alert com botões.
 */
export function confirmAction({
  title,
  message,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  destructive = false,
  onConfirm,
}: ConfirmOptions) {
  if (Platform.OS === 'web') {
    const text = message ? `${title}\n\n${message}` : title;
    if (typeof window !== 'undefined' && window.confirm(text)) onConfirm();
    return;
  }

  Alert.alert(title, message, [
    { text: cancelLabel, style: 'cancel' },
    { text: confirmLabel, style: destructive ? 'destructive' : 'default', onPress: onConfirm },
  ]);
}
