import type { ReactNode } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';
import { PressableScale } from './PressableScale';
import { Text } from './Text';

type Props = {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'deep' | 'ghost';
  disabled?: boolean;
  loading?: boolean;
  icon?: ReactNode;
};

export function Button({ title, onPress, variant = 'primary', disabled, loading, icon }: Props) {
  const { colors } = useTheme();
  const background = variant === 'primary' ? colors.primary : variant === 'deep' ? colors.deep : 'transparent';
  const foreground = variant === 'ghost' ? 'primary' : 'onDeep';
  return (
    <PressableScale
      onPress={onPress}
      disabled={disabled || loading}
      accessibilityLabel={title}
      style={{
        backgroundColor: background,
        borderRadius: 14,
        paddingVertical: 14,
        paddingHorizontal: 18,
        opacity: disabled ? 0.5 : 1,
        borderWidth: variant === 'ghost' ? 1 : 0,
        borderColor: colors.line,
      }}
    >
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
        {loading ? <ActivityIndicator color={colors.onDeep} /> : icon}
        <Text variant="body" weight={700} color={foreground}>
          {title}
        </Text>
      </View>
    </PressableScale>
  );
}
