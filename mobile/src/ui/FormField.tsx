import { TextInput, View, type TextInputProps } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';
import { fontFamily, radius } from '@/theme/tokens';
import { Text } from './Text';

type Props = TextInputProps & { label: string; error?: string | null; mono?: boolean };

export function FormField({ label, error, mono, style, ...rest }: Props) {
  const { colors } = useTheme();
  return (
    <View style={{ gap: 6 }}>
      <Text variant="label" color="inkMuted">
        {label}
      </Text>
      <TextInput
        placeholderTextColor={colors.inkMuted}
        {...rest}
        style={[
          {
            backgroundColor: colors.surface,
            borderRadius: radius.input,
            borderWidth: 1,
            borderColor: error ? colors.danger : colors.line,
            paddingHorizontal: 12,
            paddingVertical: 12,
            fontFamily: mono ? fontFamily.mono : fontFamily[500],
            fontSize: 15,
            color: colors.ink,
          },
          style,
        ]}
      />
      {error ? (
        <Text variant="label" color="danger">
          {error}
        </Text>
      ) : null}
    </View>
  );
}
