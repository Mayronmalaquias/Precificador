import { forwardRef, useState } from 'react';
import { Pressable, StyleSheet, TextInput, View, type TextInputProps } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius, Spacing, Typography } from '@/theme';
import { ThemedText } from '@/components/themed-text';

type Props = TextInputProps & {
  label?: string;
  error?: string;
  icon?: keyof typeof Ionicons.glyphMap;
  /** Campo de senha: mostra toggle de visibilidade. */
  password?: boolean;
};

export const TextField = forwardRef<TextInput, Props>(function TextField(
  { label, error, icon, password, style, onFocus, onBlur, editable = true, ...rest },
  ref,
) {
  const { colors } = useAppTheme();
  const [focused, setFocused] = useState(false);
  const [hidden, setHidden] = useState(true);

  const borderColor = error
    ? colors.danger
    : focused
      ? colors.brand
      : colors.border;

  return (
    <View style={styles.group}>
      {label && (
        <ThemedText style={[Typography.label, { color: colors.textSecondary }]}>
          {label}
        </ThemedText>
      )}

      <View
        style={[
          styles.field,
          {
            backgroundColor: editable ? colors.inputBg : colors.surfaceAlt,
            borderColor,
            borderWidth: focused ? 1.5 : StyleSheet.hairlineWidth,
          },
        ]}>
        {icon && (
          <Ionicons
            name={icon}
            size={20}
            color={focused ? colors.brand : colors.textMuted}
            style={styles.leftIcon}
          />
        )}

        <TextInput
          ref={ref}
          style={[styles.input, Typography.body, { color: colors.text }, style]}
          placeholderTextColor={colors.placeholder}
          secureTextEntry={password ? hidden : rest.secureTextEntry}
          editable={editable}
          onFocus={(e) => {
            setFocused(true);
            onFocus?.(e);
          }}
          onBlur={(e) => {
            setFocused(false);
            onBlur?.(e);
          }}
          {...rest}
        />

        {password && (
          <Pressable
            onPress={() => setHidden((v) => !v)}
            hitSlop={10}
            accessibilityRole="button"
            accessibilityLabel={hidden ? 'Mostrar senha' : 'Ocultar senha'}>
            <Ionicons
              name={hidden ? 'eye-outline' : 'eye-off-outline'}
              size={20}
              color={colors.textMuted}
            />
          </Pressable>
        )}
      </View>

      {error && (
        <ThemedText style={[Typography.caption, { color: colors.danger }]}>{error}</ThemedText>
      )}
    </View>
  );
});

const styles = StyleSheet.create({
  group: { gap: Spacing.two },
  field: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.three,
    minHeight: 54,
  },
  leftIcon: { marginRight: Spacing.two },
  input: {
    flex: 1,
    paddingVertical: Spacing.three,
  },
});
