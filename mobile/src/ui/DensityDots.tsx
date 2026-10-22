import { View } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';

/** Sunucunun 0–3 ölçekli 12 kovalık yoğunluğu; 0 = boş nokta. */
export function DensityDots({ levels }: { levels: number[] }) {
  const { colors } = useTheme();
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 2 }}>
      {levels.map((level, i) => (
        <View
          key={i}
          style={{
            width: 4,
            height: level === 0 ? 4 : 4 + level * 3,
            borderRadius: 2,
            backgroundColor: level === 0 ? colors.line : colors.primary,
            opacity: level === 0 ? 1 : 0.45 + level * 0.18,
          }}
        />
      ))}
    </View>
  );
}
