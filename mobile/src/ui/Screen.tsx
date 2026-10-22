import type { ReactNode } from 'react';
import { RefreshControl, ScrollView, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useTheme } from '@/theme/ThemeProvider';

export const TAB_BAR_SPACE = 96;

type Props = {
  children: ReactNode;
  scroll?: boolean;
  refreshing?: boolean;
  onRefresh?: () => void;
  padded?: boolean;
  edges?: ('top' | 'bottom')[];
};

export function Screen({ children, scroll = true, refreshing = false, onRefresh, padded = true, edges = ['top'] }: Props) {
  const { colors } = useTheme();
  const padding = padded ? 16 : 0;
  return (
    <SafeAreaView edges={edges} style={{ flex: 1, backgroundColor: colors.bg }}>
      {scroll ? (
        <ScrollView
          contentContainerStyle={{ padding, paddingBottom: TAB_BAR_SPACE, gap: 12 }}
          refreshControl={onRefresh ? <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} /> : undefined}
        >
          {children}
        </ScrollView>
      ) : (
        <View style={{ flex: 1, padding }}>{children}</View>
      )}
    </SafeAreaView>
  );
}
