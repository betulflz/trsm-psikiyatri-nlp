import Svg, { Path, Rect } from 'react-native-svg';
import { useTheme } from '@/theme/ThemeProvider';

export function Logo({ size = 56 }: { size?: number }) {
  const { colors } = useTheme();
  return (
    <Svg width={size} height={size} viewBox="0 0 54 54">
      <Rect x={9} y={14} width={38} height={32} rx={4} fill={colors.accent} />
      <Path d="M5 12a4 4 0 0 1 4-4h12l4 5h20a4 4 0 0 1 4 4v25a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4z" fill={colors.primary} />
      <Rect x={13} y={24} width={22} height={5} rx={1} fill={colors.highlight} />
      <Rect x={13} y={33} width={28} height={2.5} rx={1} fill="#FFFFFF" opacity={0.7} />
    </Svg>
  );
}
