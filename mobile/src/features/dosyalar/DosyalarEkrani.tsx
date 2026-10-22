import { FlashList } from '@shopify/flash-list';
import { FolderSearch } from 'lucide-react-native';
import { useMemo, useState } from 'react';
import { View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useHastalar } from '@/api/hooks';
import { useTheme } from '@/theme/ThemeProvider';
import { EmptyState, ErrorState, FilterChips, SearchField, Skeleton, TAB_BAR_SPACE, Text } from '@/ui';
import { DosyaKarti } from './DosyaKarti';
import { filterPatients, type Filtre } from './filtre';

export function DosyalarEkrani() {
  const { colors } = useTheme();
  const query = useHastalar();
  const [arama, setArama] = useState('');
  const [filtre, setFiltre] = useState<Filtre>('tumu');
  const all = useMemo(() => query.data ?? [], [query.data]);
  const list = useMemo(() => filterPatients(all, arama, filtre), [all, arama, filtre]);
  const okunmamis = all.filter((p) => p.okunmamis).length;

  return (
    <SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: colors.bg }}>
      <View style={{ paddingHorizontal: 16, paddingTop: 8, gap: 10 }}>
        <Text variant="title">Dosyalar</Text>
        <SearchField value={arama} onChangeText={setArama} placeholder="İsimle ara" />
        <FilterChips<Filtre>
          value={filtre}
          onChange={setFiltre}
          options={[
            { value: 'tumu', label: `Tümü ${all.length || ''}`.trim() },
            { value: 'son', label: 'Son ziyaret' },
            { value: 'okunmadi', label: `Okunmadı ${okunmamis}` },
          ]}
        />
      </View>
      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : query.isPending ? (
        <View style={{ padding: 16, gap: 8 }}>
          {Array.from({ length: 7 }, (_, i) => (
            <Skeleton key={i} height={62} radius={18} />
          ))}
        </View>
      ) : (
        <FlashList
          data={list}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item, index }) => <DosyaKarti hasta={item} index={index} />}
          contentContainerStyle={{ padding: 16, paddingBottom: TAB_BAR_SPACE }}
          onRefresh={() => query.refetch()}
          refreshing={query.isRefetching}
          keyboardDismissMode="on-drag"
          ListEmptyComponent={
            <EmptyState
              icon={<FolderSearch size={36} color={colors.inkMuted} />}
              title="Sonuç yok"
              message={arama ? `"${arama}" ile eşleşen dosya bulunamadı.` : 'Bu filtrede dosya yok.'}
            />
          }
        />
      )}
    </SafeAreaView>
  );
}
