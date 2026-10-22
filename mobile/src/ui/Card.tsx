import type { ReactNode } from 'react';
import { View, type StyleProp, type ViewStyle } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';
import { radius } from '@/theme/tokens';

export function Card({ style, children }: { style?: StyleProp<ViewStyle>; children: ReactNode }) {
  const { colors, name } = useTheme();
  return (
    <View
      style={[
        {
          backgroundColor: colors.surface,
          borderRadius: radius.card,
          padding: 14,
          borderWidth: name === 'dark' ? 1 : 0,
          borderColor: colors.line,
          shadowColor: '#0D1B24',
          shadowOpacity: name === 'light' ? 0.06 : 0,
          shadowRadius: 12,
          shadowOffset: { width: 0, height: 4 },
          elevation: name === 'light' ? 2 : 0,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}
