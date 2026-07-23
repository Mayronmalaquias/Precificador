import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

import { useAppTheme } from '@/hooks/use-app-theme';
import { Typography } from '@/theme';

export default function TabsLayout() {
  const { colors } = useAppTheme();

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
          height: 64,
          paddingTop: 6,
          paddingBottom: 10,
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
