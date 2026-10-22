import { useEffect } from 'react';
import Animated, { useAnimatedStyle, useReducedMotion, useSharedValue, withDelay, withSpring, withTiming } from 'react-native-reanimated';
import { useTheme } from '@/theme/ThemeProvider';
import { Text } from './Text';

/** Eğik "kaşe"; yukarıdan büyükçe gelip yaylanarak basılır. */
export function Stamp({ title, subtitle }: { title: string; subtitle: string }) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  const scale = useSharedValue(reduced ? 1 : 2.2);
  const opacity = useSharedValue(reduced ? 1 : 0);
  useEffect(() => {
    if (reduced) return;
    scale.value = withDelay(250, withSpring(1, { damping: 9, stiffness: 180 }));
    opacity.value = withDelay(250, withTiming(1, { duration: 180 }));
  }, [reduced, scale, opacity]);
  const style = useAnimatedStyle(() => ({ opacity: opacity.value, transform: [{ rotate: '-6deg' }, { scale: scale.value }] }));
  return (
    <Animated.View
      style={[
        { alignSelf: 'center', borderWidth: 3, borderColor: colors.danger, borderRadius: 8, paddingHorizontal: 16, paddingVertical: 7, alignItems: 'center' },
        style,
      ]}
    >
      <Text variant="heading" weight={800} color="danger" style={{ letterSpacing: 0.6 }}>
        {title}
      </Text>
      <Text variant="label" weight={700} color="danger" style={{ letterSpacing: 1.6 }}>
        {subtitle}
      </Text>
    </Animated.View>
  );
}
