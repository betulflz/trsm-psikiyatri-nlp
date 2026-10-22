import { CloudOff } from 'lucide-react-native';
import type { ReactNode } from 'react';
import { View } from 'react-native';
import { describeError } from '@/api/errors';
import { useTheme } from '@/theme/ThemeProvider';
import { Button } from './Button';
import { Text } from './Text';

export function ErrorState({ error, onRetry, extra }: { error: unknown; onRetry?: () => void; extra?: ReactNode }) {
  const { colors } = useTheme();
  const { title, message } = describeError(error);
  return (
    <View style={{ alignItems: 'center', padding: 24, gap: 10 }}>
      <CloudOff size={36} color={colors.danger} strokeWidth={2} />
      <Text variant="heading" style={{ textAlign: 'center' }}>
        {title}
      </Text>
      <Text variant="bodySmall" color="inkMuted" style={{ textAlign: 'center' }}>
        {message}
      </Text>
      {extra}
      {onRetry ? <Button title="Tekrar dene" onPress={onRetry} variant="deep" /> : null}
    </View>
  );
}
