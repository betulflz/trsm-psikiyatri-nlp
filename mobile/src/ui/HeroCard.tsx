import type { ReactNode } from 'react';
import { View, type StyleProp, type ViewStyle } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';
import { radius } from '@/theme/tokens';

/** `deep` zeminli vurgu kartı; sağ üstte yarı saydam ana renk halkası. */
export function HeroCard({ style, children }: { style?: StyleProp<ViewStyle>; children: ReactNode }) {
  const { colors } = useTheme();
  return (
    <View style={[{ backgroundColor: colors.deep, borderRadius: radius.hero, padding: 16, overflow: 'hidden' }, style]}>
      <View
        pointerEvents="none"
        style={{
          position: 'absolute',
          right: -36,
          top: -36,
          width: 130,
          height: 130,
          borderRadius: 65,
          backgroundColor: colors.primary,
          opacity: 0.4,
        }}
      />
      {children}
    </View>
  );
}
