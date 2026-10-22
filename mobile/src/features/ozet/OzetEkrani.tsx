import { View } from 'react-native';
import Animated, { FadeInDown, useReducedMotion } from 'react-native-reanimated';
import { useOzet } from '@/api/hooks';
import { useAuth } from '@/auth/AuthProvider';
import { formatNumber, initials } from '@/lib/format';
import { useTheme } from '@/theme/ThemeProvider';
import { BarChart, Card, Chip, Donut, ErrorState, HBarList, HeroCard, Screen, Skeleton, StatTile, Text, useCountUp } from '@/ui';

function todayLabel() {
  try {
    return new Intl.DateTimeFormat('tr-TR', { day: 'numeric', month: 'long', weekday: 'long' }).format(new Date());
  } catch {
    return '';
  }
}

export function OzetEkrani() {
  const { colors } = useTheme();
  const { user } = useAuth();
  const reduced = useReducedMotion();
  const query = useOzet();
  const data = query.data;
  const total = useCountUp(data?.toplam_dosya ?? 0);
  const enter = (i: number) => (reduced ? undefined : FadeInDown.delay(i * 60).duration(500));

  return (
    <Screen refreshing={query.isRefetching} onRefresh={() => query.refetch()}>
      <Animated.View entering={enter(0)} style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <View>
          <Text variant="label" color="inkMuted">
            {todayLabel()}
          </Text>
          <Text variant="title">Arşiv özeti</Text>
        </View>
        <View style={{ width: 40, height: 40, borderRadius: 13, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center' }}>
          <Text variant="bodySmall" weight={800} color="onAccent">
            {initials(user?.ad_soyad ?? '')}
          </Text>
        </View>
      </Animated.View>

      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : !data ? (
        <View style={{ gap: 12 }}>
          <Skeleton height={190} radius={22} />
          <View style={{ flexDirection: 'row', gap: 12 }}>
            <View style={{ flex: 1 }}>
              <Skeleton height={110} radius={18} />
            </View>
            <View style={{ flex: 1 }}>
              <Skeleton height={110} radius={18} />
            </View>
          </View>
          <Skeleton height={150} radius={18} />
        </View>
      ) : (
        <>
          <Animated.View entering={enter(1)}>
            <HeroCard>
              <Text variant="label" color="onDeep" style={{ opacity: 0.7 }}>
                Toplam dosya
              </Text>
              <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 8 }}>
                <Text variant="display" color="onDeep">
                  {formatNumber(total)}
                </Text>
                {data.okunmamis_rapor > 0 && <Chip label={`+${data.okunmamis_rapor} okunmadı`} tone="accent" />}
              </View>
              <View style={{ marginTop: 12 }}>
                <BarChart
                  onDeep
                  height={52}
                  highlightIndex={data.yillik_not.length - 1}
                  data={data.yillik_not.map((y, i) => ({ label: i === 0 ? String(y.yil) : `'${String(y.yil).slice(2)}`, value: y.sayi }))}
                />
              </View>
            </HeroCard>
          </Animated.View>

          <Animated.View entering={enter(2)} style={{ flexDirection: 'row', gap: 12 }}>
            <StatTile
              label="Ziyaret notu"
              value={data.toplam_not}
              progress={data.toplam_not ? data.ilacli_not / data.toplam_not : 0}
              footnote={`%${data.toplam_not ? Math.round((data.ilacli_not / data.toplam_not) * 100) : 0}'inde ilaç okundu`}
            />
            <Card style={{ flex: 1, alignItems: 'center', gap: 6 }}>
              <Donut
                size={68}
                segments={[
                  { value: data.cinsiyet.erkek, color: colors.primary },
                  { value: data.cinsiyet.kadin, color: colors.accent },
                ]}
              />
              <Text variant="label">
                <Text variant="label" style={{ color: colors.primary }}>
                  ●{' '}
                </Text>
                {data.cinsiyet.erkek} E{'   '}
                <Text variant="label" style={{ color: colors.accent }}>
                  ●{' '}
                </Text>
                {data.cinsiyet.kadin} K
              </Text>
            </Card>
          </Animated.View>

          <Animated.View entering={enter(3)}>
            <Card style={{ gap: 10 }}>
              <Text variant="label" color="inkMuted">
                En sık okunan ilaçlar
              </Text>
              <HBarList items={data.en_sik_ilaclar.map((d) => ({ label: d.ilac, value: d.sayi }))} />
            </Card>
          </Animated.View>
        </>
      )}
    </Screen>
  );
}
