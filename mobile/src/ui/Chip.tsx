import { View } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';
import { radius, type Colors } from '@/theme/tokens';
import { Text } from './Text';

type Tone = 'neutral' | 'primary' | 'highlight' | 'danger' | 'accent';

const TONES: Record<Tone, { bg: keyof Colors; fg: keyof Colors }> = {
  neutral: { bg: 'line', fg: 'ink' },
  primary: { bg: 'primarySoft', fg: 'primary' },
  highlight: { bg: 'highlight', fg: 'highlightInk' },
  danger: { bg: 'dangerSoft', fg: 'danger' },
  accent: { bg: 'accent', fg: 'onAccent' },
};

export function Chip({ label, tone = 'neutral' }: { label: string; tone?: Tone }) {
  const { colors } = useTheme();
  const t = TONES[tone];
  return (
    <View
      style={{ backgroundColor: colors[t.bg], borderRadius: radius.chip, paddingHorizontal: 8, paddingVertical: 3, alignSelf: 'flex-start' }}
    >
      <Text variant="label" weight={700} color={t.fg}>
        {label}
      </Text>
    </View>
  );
}
