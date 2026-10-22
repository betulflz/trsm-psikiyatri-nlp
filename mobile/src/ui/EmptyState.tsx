import type { ReactNode } from 'react';
import { View } from 'react-native';
import { Text } from './Text';

export function EmptyState({ title, message, icon }: { title: string; message: string; icon?: ReactNode }) {
  return (
    <View style={{ alignItems: 'center', paddingVertical: 40, paddingHorizontal: 24, gap: 8 }}>
      {icon}
      <Text variant="heading" style={{ textAlign: 'center' }}>
        {title}
      </Text>
      <Text variant="bodySmall" color="inkMuted" style={{ textAlign: 'center' }}>
        {message}
      </Text>
    </View>
  );
}
