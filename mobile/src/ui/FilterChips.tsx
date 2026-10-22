import { ScrollView } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';
import { PressableScale } from './PressableScale';
import { Text } from './Text';

type Props<T extends string> = { options: { value: T; label: string }[]; value: T; onChange: (value: T) => void };

export function FilterChips<T extends string>({ options, value, onChange }: Props<T>) {
  const { colors } = useTheme();
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 6 }}>
      {options.map((option) => {
        const active = option.value === value;
        return (
          <PressableScale
            key={option.value}
            onPress={() => onChange(option.value)}
            accessibilityLabel={option.label}
            style={{
              backgroundColor: active ? colors.deep : colors.surface,
              borderColor: colors.line,
              borderWidth: active ? 0 : 1,
              borderRadius: 10,
              paddingHorizontal: 12,
              paddingVertical: 6,
            }}
          >
            <Text variant="bodySmall" weight={600} color={active ? 'onDeep' : 'ink'}>
              {option.label}
            </Text>
          </PressableScale>
        );
      })}
    </ScrollView>
  );
}
