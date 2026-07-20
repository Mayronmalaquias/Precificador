import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { Animated, Platform, Pressable, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius, Spacing, Typography, shadow } from '@/theme';
import { ThemedText } from '@/components/themed-text';

// No web não há módulo nativo de animação — evita warning e usa fallback JS.
const USE_NATIVE = Platform.OS !== 'web';

type ToastType = 'success' | 'error' | 'info';
type ToastOptions = { type?: ToastType; message: string; duration?: number };

type ToastContextValue = { show: (opts: ToastOptions) => void };
const ToastContext = createContext<ToastContextValue | null>(null);

const ICON: Record<ToastType, keyof typeof Ionicons.glyphMap> = {
  success: 'checkmark-circle',
  error: 'alert-circle',
  info: 'information-circle',
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastOptions | null>(null);
  // useState (init lazy) mantém a Animated.Value estável sem ler ref.current no render.
  const [opacity] = useState(() => new Animated.Value(0));
  const [translateY] = useState(() => new Animated.Value(-16));
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { colors, isDark } = useAppTheme();
  const insets = useSafeAreaInsets();

  const dismiss = useCallback(() => {
    Animated.parallel([
      Animated.timing(opacity, { toValue: 0, duration: 180, useNativeDriver: USE_NATIVE }),
      Animated.timing(translateY, { toValue: -16, duration: 180, useNativeDriver: USE_NATIVE }),
    ]).start(() => setToast(null));
  }, [opacity, translateY]);

  const show = useCallback(
    ({ type = 'info', message, duration = 3200 }: ToastOptions) => {
      if (hideTimer.current) clearTimeout(hideTimer.current);
      setToast({ type, message });
      opacity.setValue(0);
      translateY.setValue(-16);
      Animated.parallel([
        Animated.timing(opacity, { toValue: 1, duration: 220, useNativeDriver: USE_NATIVE }),
        Animated.spring(translateY, { toValue: 0, useNativeDriver: USE_NATIVE, friction: 8 }),
      ]).start();
      hideTimer.current = setTimeout(dismiss, duration);
    },
    [opacity, translateY, dismiss],
  );

  const value = useMemo(() => ({ show }), [show]);

  const accent =
    toast?.type === 'success'
      ? colors.success
      : toast?.type === 'error'
        ? colors.danger
        : colors.brand;

  return (
    <ToastContext.Provider value={value}>
      {children}
      {toast && (
        <View style={[styles.host, { top: insets.top + Spacing.two, pointerEvents: 'box-none' }]}>
          <Animated.View style={{ opacity, transform: [{ translateY }], width: '100%' }}>
            <Pressable
              onPress={dismiss}
              style={[
                styles.toast,
                shadow('md', isDark),
                { backgroundColor: colors.surface, borderColor: colors.border },
              ]}>
              <View style={[styles.iconWrap, { backgroundColor: accent + '22' }]}>
                <Ionicons name={ICON[toast.type ?? 'info']} size={20} color={accent} />
              </View>
              <ThemedText
                style={[Typography.caption, { color: colors.text, flex: 1 }]}
                numberOfLines={3}>
                {toast.message}
              </ThemedText>
            </Pressable>
          </Animated.View>
        </View>
      )}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast deve ser usado dentro de <ToastProvider>');
  return ctx;
}

const styles = StyleSheet.create({
  host: {
    position: 'absolute',
    left: Spacing.three,
    right: Spacing.three,
    alignItems: 'center',
    zIndex: 999,
  },
  toast: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    paddingVertical: Spacing.two + 2,
    paddingHorizontal: Spacing.three,
    borderRadius: Radius.md,
    borderWidth: StyleSheet.hairlineWidth,
  },
  iconWrap: {
    width: 32,
    height: 32,
    borderRadius: Radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
