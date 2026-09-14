import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useAppTheme } from '@/hooks/use-app-theme';
import { Typography } from '@/theme';

/** Altura útil da barra: ícone + rótulo, sem contar a área do sistema. */
const ALTURA_CONTEUDO = 48;
const PADDING_TOPO = 6;
const PADDING_BASE = 10;

export default function TabsLayout() {
  const { colors } = useAppTheme();
  // O Android desenha edge-to-edge desde o SDK 54, entao a barra fica POR BAIXO da
  // navegacao do sistema. O React Navigation soma a safe area sozinho, mas `height` e
  // `paddingBottom` explicitos em `tabBarStyle` substituem essa conta — era por isso que
  // os rotulos apareciam atras dos botoes do celular. Somando o inset aqui, a barra cresce
  // exatamente o que o sistema ocupa e o conteudo dela nao se move.
  const insets = useSafeAreaInsets();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.brand,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          borderTopWidth: 0.5,
          height: ALTURA_CONTEUDO + PADDING_TOPO + PADDING_BASE + insets.bottom,
          paddingTop: PADDING_TOPO,
          paddingBottom: PADDING_BASE + insets.bottom,
        },
        tabBarLabelStyle: { ...Typography.caption, fontSize: 11 },
        sceneStyle: { backgroundColor: colors.canvas },
      }}>
      {/* Home pública */}
      <Tabs.Screen
        name="index"
        options={{
          title: 'Precificador',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="calculator-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="financiamento"
        options={{
          title: '61 Financeiro',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="cash-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="visita"
        options={{
          title: 'Visita',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="add-circle-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="captacao"
        options={{
          title: 'Captação',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="git-branch-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="registros"
        options={{
          title: 'Registros',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="albums-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="perfil"
        options={{
          title: 'Perfil',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="person-circle-outline" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
