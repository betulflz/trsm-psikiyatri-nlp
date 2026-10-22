import { useEffect } from 'react';
import Animated, { Easing, useAnimatedProps, useReducedMotion, useSharedValue, withDelay, withTiming } from 'react-native-reanimated';
import Svg, { Circle } from 'react-native-svg';
import { useTheme } from '@/theme/ThemeProvider';

const AnimatedCircle = Animated.createAnimatedComponent(Circle);
type Segment = { value: number; color: string };

function Arc({
  c, r, stroke, circumference, fraction, startFraction, color, delay,
}: {
  c: number; r: number; stroke: number; circumference: number; fraction: number; startFraction: number; color: string; delay: number;
}) {
  const reduced = useReducedMotion();
  const progress = useSharedValue(reduced ? 1 : 0);
  useEffect(() => {
    if (!reduced) progress.value = withDelay(delay, withTiming(1, { duration: 900, easing: Easing.out(Easing.cubic) }));
  }, [reduced, delay, progress]);
  const animatedProps = useAnimatedProps(() => ({
    strokeDashoffset: circumference - circumference * fraction * progress.value,
  }));
  return (
    <AnimatedCircle
      cx={c}
      cy={c}
      r={r}
      fill="none"
      stroke={color}
      strokeWidth={stroke}
      strokeDasharray={`${circumference} ${circumference}`}
      rotation={-90 + 360 * startFraction}
      origin={`${c}, ${c}`}
      animatedProps={animatedProps}
    />
  );
}

export function Donut({ segments, size = 64, stroke = 9 }: { segments: Segment[]; size?: number; stroke?: number }) {
  const { colors } = useTheme();
  const c = size / 2;
  const r = c - stroke / 2;
  const circumference = 2 * Math.PI * r;
  const total = segments.reduce((sum, s) => sum + s.value, 0) || 1;
  let start = 0;
  return (
    <Svg width={size} height={size}>
      <Circle cx={c} cy={c} r={r} fill="none" stroke={colors.primarySoft} strokeWidth={stroke} />
      {segments.map((segment, i) => {
        const fraction = segment.value / total;
        const arc = (
          <Arc
            key={i}
            c={c}
            r={r}
            stroke={stroke}
            circumference={circumference}
            fraction={fraction}
            startFraction={start}
            color={segment.color}
            delay={300 + i * 200}
          />
        );
        start += fraction;
        return arc;
      })}
    </Svg>
  );
}
