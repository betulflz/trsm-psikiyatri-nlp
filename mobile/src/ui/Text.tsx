import { Text as RNText, type TextProps } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';
import { fontFamily, typeScale, type Colors, type FontWeight, type TypeVariant } from '@/theme/tokens';

type Props = TextProps & { variant?: TypeVariant; color?: keyof Colors; weight?: FontWeight };

export function Text({ variant = 'body', color = 'ink', weight, style, ...rest }: Props) {
  const { colors } = useTheme();
  const scale = typeScale[variant];
  const family = variant === 'mono' ? fontFamily.mono : fontFamily[weight ?? scale.weight];
  return (
    <RNText
      maxFontSizeMultiplier={1.3}
      {...rest}
      style={[
        {
          fontFamily: family,
          fontSize: scale.fontSize,
          lineHeight: scale.lineHeight,
          letterSpacing: scale.letterSpacing,
          color: colors[color],
        },
        style,
      ]}
    />
  );
}
