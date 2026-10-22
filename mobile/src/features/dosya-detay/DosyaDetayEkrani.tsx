import { FlashList } from '@shopify/flash-list';
import { router } from 'expo-router';
import { ChevronLeft } from 'lucide-react-native';
import { ActivityIndicator, Pressable, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useHasta, useNotlar } from '@/api/hooks';
import type { HastaDetayi } from '@/api/types';
import { formatDate, initials } from '@/lib/format';
import { useTheme } from '@/theme/ThemeProvider';
import { ErrorState, Skeleton, Stamp, Text, TimelineItem } from '@/ui';
import { NotKarti } from './NotKarti';

function Baslik({ hasta }: { hasta: HastaDetayi | undefined }) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const meta = hasta ? [hasta.cinsiyet, hasta.yas !== null ? `${hasta.yas}` : null].filter(Boolean).join(' · ') : '';
  return (
    <View
      style={{
        backgroundColor: colors.deep,
        paddingTop: insets.top + 6,
        paddingHorizontal: 18,
        paddingBottom: 18,
        borderBottomLeftRadius: 26,
        borderBottomRightRadius: 26,
      }}
    >
      <Pressable accessibilityLabel="Geri" onPress={() => router.back()} hitSlop={12} style={{ flexDirection: 'row', alignItems: 'center' }}>
        <ChevronLeft size={20} color={colors.onDeep} />
        <Text variant="bodySmall" color="onDeep" style={{ opacity: 0.75 }}>
          Dosyalar
        </Text>
      </Pressable>
      {!hasta ? (
        <View style={{ marginTop: 14, gap: 8 }}>
          <Skeleton height={50} width="70%" />
          <Skeleton height={54} />
        </View>
      ) : (
        <>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, marginTop: 12 }}>
            <View style={{ width: 50, height: 50, borderRadius: 16, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center' }}>
              <Text variant="heading" weight={800} color="onAccent">
                {initials(hasta.ad)}
              </Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text variant="title" color="onDeep" numberOfLines={1}>
                {hasta.ad}
              </Text>
              <Text variant="bodySmall" color="onDeep" style={{ opacity: 0.7 }}>
                {meta ? `${meta} · ` : ''}
                <Text variant="mono" color="onDeep">
                  {hasta.dosya_no}
                </Text>
              </Text>
            </View>
          </View>
          <View style={{ flexDirection: 'row', gap: 8, marginTop: 14 }}>
            {[
              [String(hasta.not_sayisi), 'not'],
              [String(hasta.ilac_sayisi), 'ilaç'],
              [hasta.ilk_kayit ? hasta.ilk_kayit.slice(0, 4) : '—', 'ilk kayıt'],
            ].map(([value, label]) => (
              <View key={label} style={{ flex: 1, backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: 12, padding: 10 }}>
                <Text variant="heading" weight={800} color="onDeep">
                  {value}
                </Text>
                <Text variant="label" weight={500} color="onDeep" style={{ opacity: 0.7 }}>
                  {label}
                </Text>
              </View>
            ))}
          </View>
        </>
      )}
    </View>
  );
}

export function DosyaDetayEkrani({ id }: { id: number }) {
  const { colors } = useTheme();
  const hasta = useHasta(id);
  const notlar = useNotlar(id);
  const items = notlar.data?.pages.flatMap((p) => p.notlar) ?? [];

  if (hasta.isError) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.bg }}>
        <Baslik hasta={undefined} />
        <ErrorState error={hasta.error} onRetry={() => hasta.refetch()} />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <FlashList
        data={items}
        keyExtractor={(n) => String(n.id)}
        ListHeaderComponent={
          <View style={{ marginBottom: 16 }}>
            <Baslik hasta={hasta.data} />
          </View>
        }
        renderItem={({ item, index }) => (
          <View style={{ paddingHorizontal: 16 }}>
            <TimelineItem
              index={index}
              latest={index === 0}
              isLast={index === items.length - 1 && !notlar.hasNextPage}
              title={formatDate(item.tarih)}
              subtitle={item.sayfa_no ? `sayfa ${item.sayfa_no}` : undefined}
            >
              <NotKarti not={item} />
            </TimelineItem>
          </View>
        )}
        onEndReachedThreshold={0.6}
        onEndReached={() => {
          if (notlar.hasNextPage && !notlar.isFetchingNextPage) notlar.fetchNextPage();
        }}
        ListEmptyComponent={
          notlar.isPending ? (
            <View style={{ padding: 16, gap: 10 }}>
              <Skeleton height={120} radius={18} />
              <Skeleton height={120} radius={18} />
            </View>
          ) : notlar.isError ? (
            <ErrorState error={notlar.error} onRetry={() => notlar.refetch()} />
          ) : (
            <View style={{ paddingTop: 30, gap: 16, paddingHorizontal: 24 }}>
              <Stamp title="HENÜZ OKUNMADI" subtitle="ANALİZ EDİLMİŞ RAPOR YOK" />
              <Text variant="bodySmall" color="inkMuted" style={{ textAlign: 'center' }}>
                Bu dosyada OCR'dan geçmiş not bulunmuyor.
              </Text>
            </View>
          )
        }
        ListFooterComponent={
          notlar.isFetchingNextPage ? <ActivityIndicator style={{ marginVertical: 20 }} color={colors.primary} /> : <View style={{ height: 40 }} />
        }
      />
    </View>
  );
}
