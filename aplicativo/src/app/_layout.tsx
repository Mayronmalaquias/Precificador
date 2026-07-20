import { useEffect } from 'react';
import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { ToastProvider } from '@/components/ui/toast';
import { SessionProvider, useSession } from '@/features/auth/session';
import { useAppTheme } from '@/hooks/use-app-theme';

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <SessionProvider>
          <ToastProvider>
            <RootNavigator />
          </ToastProvider>
        </SessionProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

function RootNavigator() {
  const { isAuthenticated, isLoading } = useSession();
  const { isDark } = useAppTheme();

  // Só esconde o splash quando a sessão foi reidratada do storage.
  useEffect(() => {
    if (!isLoading) SplashScreen.hideAsync();
  }, [isLoading]);

  if (isLoading) return null;

  return (
    <ThemeProvider value={isDark ? DarkTheme : DefaultTheme}>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <Stack screenOptions={{ headerShown: false }}>
        {/* Tabs sempre acessíveis — o Precificador é público. */}
        <Stack.Screen name="(tabs)" />
        {/* Login só existe quando deslogado; ao autenticar o guard fecha a rota
            (Stack.Protected, docs Expo Router v57). */}
        <Stack.Protected guard={!isAuthenticated}>
          <Stack.Screen name="login" options={{ presentation: 'modal' }} />
        </Stack.Protected>
      </Stack>
    </ThemeProvider>
  );
}
