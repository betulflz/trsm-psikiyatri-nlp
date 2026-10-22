import type { ReactNode } from 'react';
import { View } from 'react-native';
import Animated, { FadeInDown, useReducedMotion } from 'react-native-reanimated';
import { useTheme } from '@/theme/ThemeProvider';
import { Text } from './Text';

type Props = { title: string; subtitle?: string; latest?: boolean; index: number; isLast?: boolean; children?: ReactNode };

export function TimelineItem({ title, subtitle, latest = false, index, isLast = false, children }: Props) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  const entering = reduced ? undefined : FadeInDown.delay(Math.min(index, 8) * 60).duration(450);
  return (
    <Animated.View entering={entering} style={{ flexDirection: 'row', gap: 12 }}>
      <View style={{ width: 14, alignItems: 'center' }}>
        <View
          style={{
            marginTop: 3,
            width: 12,
            height: 12,
            borderRadius: 6,
            backgroundColor: latest ? colors.accent : colors.surface,
            borderWidth: latest ? 0 : 2.5,
            borderColor: colors.primary,
            shadowColor: colors.accent,
            shadowOpacity: latest ? 0.9 : 0,
            shadowRadius: 6,
          }}
        />
        {!isLast && <View style={{ flex: 1, width: 2, backgroundColor: colors.line, marginTop: 4 }} />}
      </View>
      <View style={{ flex: 1, paddingBottom: 18, gap: 7 }}>
        <Text variant="bodySmall" weight={700}>
          {title}
          {subtitle ? (
            <Text variant="bodySmall" color="inkMuted">
              {`  ·  ${subtitle}`}
            </Text>
          ) : null}
        </Text>
        {children}
      </View>
    </Animated.View>
  );
}
