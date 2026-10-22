import { router } from 'expo-router';
import { View } from 'react-native';
import Animated, { FadeInDown, useReducedMotion } from 'react-native-reanimated';
import type { HastaOzeti } from '@/api/types';
import { formatDate } from '@/lib/format';
import { useTheme } from '@/theme/ThemeProvider';
import { radius } from '@/theme/tokens';
import { Chip, DensityDots, PressableScale, Text } from '@/ui';

function subtitle(p: HastaOzeti) {
  if (p.okunmamis) return 'Ham rapor · okunmadı';
  if (p.not_sayisi === 0) return 'Not yok';
  if (!p.son_ziyaret) return `${p.not_sayisi} not · tarihli not yok`;
  return `${p.not_sayisi} not · son ${formatDate(p.son_ziyaret)}`;
}

export function DosyaKarti({ hasta, index }: { hasta: HastaOzeti; index: number }) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  return (
    <Animated.View entering={reduced || index > 10 ? undefined : FadeInDown.delay(index * 50).duration(400)}>
      <PressableScale
        accessibilityLabel={`${hasta.ad} dosyasını aç`}
        onPress={() => router.push(`/dosya/${hasta.id}`)}
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: 12,
          backgroundColor: colors.surface,
          borderRadius: radius.card,
          padding: 12,
          marginBottom: 8,
        }}
      >
        <View style={{ width: 5, alignSelf: 'stretch', borderRadius: 3, backgroundColor: hasta.okunmamis ? colors.danger : colors.primary }} />
        <View style={{ flex: 1, gap: 2 }}>
          <Text variant="body" weight={700} numberOfLines={1}>
            {hasta.ad}
          </Text>
          <Text variant="label" weight={500} color={hasta.okunmamis ? 'danger' : 'inkMuted'}>
            {subtitle(hasta)}
          </Text>
        </View>
        {hasta.okunmamis ? <Chip label="YENİ" tone="danger" /> : <DensityDots levels={hasta.yogunluk} />}
      </PressableScale>
    </Animated.View>
  );
}
