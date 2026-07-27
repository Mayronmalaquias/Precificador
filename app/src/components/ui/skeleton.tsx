import { useEffect, useState } from 'react';
import { Animated, Platform, type DimensionValue, type ViewStyle } from 'react-native';

import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius } from '@/theme';

const USE_NATIVE = Platform.OS !== 'web';

type Props = {
  width?: DimensionValue;
  height?: number;
  radius?: number;
  style?: ViewStyle;
};

/** Bloco de carregamento com pulso suave (skeleton, não spinner). */
export function Skeleton({ width = '100%', height = 16, radius = Radius.xs, style }: Props) {
  const { colors } = useAppTheme();
  const [pulse] = useState(() => new Animated.Value(0.4));

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1, duration: 700, useNativeDriver: USE_NATIVE }),
        Animated.timing(pulse, { toValue: 0.4, duration: 700, useNativeDriver: USE_NATIVE }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [pulse]);

  return (
    <Animated.View
      style={[
        { width, height, borderRadius: radius, backgroundColor: colors.skeleton, opacity: pulse },
        style,
      ]}
    />
  );
}
