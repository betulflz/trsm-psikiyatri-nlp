import { useEffect } from 'react';
import type { DimensionValue } from 'react-native';
import Animated, { useAnimatedStyle, useReducedMotion, useSharedValue, withRepeat, withTiming } from 'react-native-reanimated';
import { useTheme } from '@/theme/ThemeProvider';

export function Skeleton({ width = '100%', height, radius = 12 }: { width?: DimensionValue; height: number; radius?: number }) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  const opacity = useSharedValue(0.5);
  useEffect(() => {
    if (!reduced) opacity.value = withRepeat(withTiming(1, { duration: 700 }), -1, true);
  }, [reduced, opacity]);
  const style = useAnimatedStyle(() => ({ opacity: opacity.value }));
  return <Animated.View style={[{ width, height, borderRadius: radius, backgroundColor: colors.line }, style]} />;
}
