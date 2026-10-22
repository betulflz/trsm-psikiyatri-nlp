import { useState } from 'react';
import { Pressable, View } from 'react-native';
import Animated, { useAnimatedStyle, withSpring } from 'react-native-reanimated';
import { useTheme } from '@/theme/ThemeProvider';
import { Text } from './Text';

type Props<T extends string> = { options: { value: T; label: string }[]; value: T; onChange: (value: T) => void };

export function SegmentedControl<T extends string>({ options, value, onChange }: Props<T>) {
  const { colors } = useTheme();
  const [width, setWidth] = useState(0);
  const index = Math.max(0, options.findIndex((o) => o.value === value));
  const segment = options.length ? (width - 6) / options.length : 0;
  const thumb = useAnimatedStyle(() => ({
    transform: [{ translateX: withSpring(index * segment, { damping: 18, stiffness: 220 }) }],
  }));
  return (
    <View
      onLayout={(e) => setWidth(e.nativeEvent.layout.width)}
      style={{ flexDirection: 'row', backgroundColor: colors.line, borderRadius: 12, padding: 3 }}
    >
      {width > 0 && (
        <Animated.View
          style={[
            { position: 'absolute', top: 3, left: 3, bottom: 3, width: segment, borderRadius: 9, backgroundColor: colors.surface },
            thumb,
          ]}
        />
      )}
      {options.map((option) => (
        <Pressable
          key={option.value}
          accessibilityRole="button"
          accessibilityState={{ selected: option.value === value }}
          onPress={() => onChange(option.value)}
          style={{ flex: 1, paddingVertical: 8, alignItems: 'center' }}
        >
          <Text variant="bodySmall" weight={option.value === value ? 700 : 500}>
            {option.label}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}
