import { useEffect } from 'react';
import { View } from 'react-native';
import Animated, { useAnimatedStyle, useReducedMotion, useSharedValue, withDelay, withTiming } from 'react-native-reanimated';
import { formatNumber } from '@/lib/format';
import { useTheme } from '@/theme/ThemeProvider';
import { Card } from './Card';
import { Text } from './Text';
import { useCountUp } from './useCountUp';

type Props = { label: string; value: number; footnote?: string; progress?: number };

export function StatTile({ label, value, footnote, progress }: Props) {
  const { colors } = useTheme();
  const shown = useCountUp(value);
  const reduced = useReducedMotion();
  const fill = useSharedValue(reduced ? progress ?? 0 : 0);
  useEffect(() => {
    if (progress === undefined) return;
    if (reduced) fill.value = progress;
    else fill.value = withDelay(400, withTiming(progress, { duration: 700 }));
  }, [progress, reduced, fill]);
  const bar = useAnimatedStyle(() => ({ width: `${fill.value * 100}%` }));
  return (
    <Card style={{ flex: 1, gap: 2 }}>
      <Text variant="label" color="inkMuted">
        {label}
      </Text>
      <Text variant="title">{formatNumber(shown)}</Text>
      {progress !== undefined && (
        <View style={{ height: 5, borderRadius: 3, backgroundColor: colors.primarySoft, overflow: 'hidden', marginTop: 6 }}>
          <Animated.View style={[{ height: '100%', backgroundColor: colors.primary }, bar]} />
        </View>
      )}
      {footnote ? (
        <Text variant="label" color="inkMuted" weight={500} style={{ marginTop: 4 }}>
          {footnote}
        </Text>
      ) : null}
    </Card>
  );
}
