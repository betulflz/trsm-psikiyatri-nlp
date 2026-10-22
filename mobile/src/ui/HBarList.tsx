import { useEffect } from 'react';
import { View } from 'react-native';
import Animated, { Easing, useAnimatedStyle, useReducedMotion, useSharedValue, withDelay, withTiming } from 'react-native-reanimated';
import { formatNumber } from '@/lib/format';
import { useTheme } from '@/theme/ThemeProvider';
import { Text } from './Text';

function Row({ label, value, ratio, index }: { label: string; value: number; ratio: number; index: number }) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  const width = useSharedValue(reduced ? ratio : 0);
  useEffect(() => {
    if (reduced) width.value = ratio;
    else width.value = withDelay(450 + index * 60, withTiming(ratio, { duration: 700, easing: Easing.out(Easing.cubic) }));
  }, [ratio, index, reduced, width]);
  const fill = useAnimatedStyle(() => ({ width: `${width.value * 100}%` }));
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
      <Text variant="bodySmall" weight={600} numberOfLines={1} style={{ width: 78 }}>
        {label}
      </Text>
      <View style={{ flex: 1, height: 8, borderRadius: 4, backgroundColor: colors.primarySoft, overflow: 'hidden' }}>
        <Animated.View style={[{ height: '100%', borderRadius: 4, backgroundColor: colors.primary }, fill]} />
      </View>
      <Text variant="mono" color="inkMuted" style={{ width: 44, textAlign: 'right' }}>
        {formatNumber(value)}
      </Text>
    </View>
  );
}

export function HBarList({ items }: { items: { label: string; value: number }[] }) {
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <View style={{ gap: 9 }}>
      {items.map((item, index) => (
        <Row key={item.label} label={item.label} value={item.value} ratio={item.value / max} index={index} />
      ))}
    </View>
  );
}
