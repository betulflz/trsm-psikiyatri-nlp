import { useEffect } from 'react';
import { View } from 'react-native';
import Animated, { useAnimatedStyle, useReducedMotion, useSharedValue, withDelay, withSpring } from 'react-native-reanimated';
import { useTheme } from '@/theme/ThemeProvider';
import { Text } from './Text';

type Datum = { label: string; value: number };
type Props = { data: Datum[]; highlightIndex?: number; height?: number; onDeep?: boolean };

function Bar({ ratio, index, color, height }: { ratio: number; index: number; color: string; height: number }) {
  const reduced = useReducedMotion();
  const h = useSharedValue(reduced ? ratio * height : 0);
  useEffect(() => {
    if (reduced) h.value = ratio * height;
    else h.value = withDelay(150 + index * 60, withSpring(ratio * height, { damping: 13, stiffness: 140 }));
  }, [ratio, height, index, reduced, h]);
  const style = useAnimatedStyle(() => ({ height: Math.max(4, h.value) }));
  return <Animated.View style={[{ flex: 1, borderRadius: 6, backgroundColor: color }, style]} />;
}

export function BarChart({ data, highlightIndex, height = 56, onDeep = false }: Props) {
  const { colors } = useTheme();
  const max = Math.max(1, ...data.map((d) => d.value));
  const muted = onDeep ? 'rgba(255,255,255,0.28)' : colors.primarySoft;
  const strong = onDeep ? colors.accent : colors.primary;
  return (
    <View>
      <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 8, height }}>
        {data.map((d, i) => (
          <Bar key={d.label} ratio={d.value / max} index={i} height={height} color={i === highlightIndex ? strong : muted} />
        ))}
      </View>
      <View style={{ flexDirection: 'row', gap: 8, marginTop: 5 }}>
        {data.map((d) => (
          <Text
            key={d.label}
            variant="label"
            color={onDeep ? 'onDeep' : 'inkMuted'}
            style={{ flex: 1, textAlign: 'center', opacity: onDeep ? 0.65 : 1 }}
          >
            {d.label}
          </Text>
        ))}
      </View>
    </View>
  );
}
