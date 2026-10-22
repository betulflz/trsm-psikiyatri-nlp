import * as ImagePicker from 'expo-image-picker';
import { ArrowLeft, ArrowRight, Camera, ImagePlus, Trash2 } from 'lucide-react-native';
import { useRef } from 'react';
import { Alert, Image, Pressable, ScrollView, View } from 'react-native';
import Animated, { FadeIn, LinearTransition } from 'react-native-reanimated';
import { useTheme } from '@/theme/ThemeProvider';
import { Button, Text } from '@/ui';
import { movePage } from './taslak';
import type { PageOcr } from './ocr';

type Props = { pages: string[]; onChange: (pages: string[]) => void; onBack: () => void; onSave: () => void; saving: boolean; ocr: Record<string, PageOcr>; reading: boolean; onRead: (uris: string[]) => Promise<void> };

export function RaporAdimi({ pages, onChange, onBack, onSave, saving, ocr, reading, onRead }: Props) {
  const { colors } = useTheme();
  const picking = useRef(false);

  async function pick(source: 'kamera' | 'galeri') {
    if (picking.current || reading || saving) return;
    picking.current = true;
    try {
      const permission =
        source === 'kamera' ? await ImagePicker.requestCameraPermissionsAsync() : await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        Alert.alert('İzin gerekli', source === 'kamera' ? 'Kamera izni verilmedi.' : 'Galeri izni verilmedi.');
        return;
      }
      const options: ImagePicker.ImagePickerOptions = { mediaTypes: ['images'], quality: 0.7, allowsMultipleSelection: source === 'galeri' };
      const result = source === 'kamera' ? await ImagePicker.launchCameraAsync(options) : await ImagePicker.launchImageLibraryAsync(options);
      if (!result.canceled) {
        const added = result.assets.map((a) => a.uri).filter((uri) => !pages.includes(uri));
        onChange([...new Set([...pages, ...added])]);
        await onRead([...new Set(added)]);
      }
    } catch {
      Alert.alert('Fotoğraf alınamadı', 'Kamera veya galeri açılamadı. Tekrar deneyin.');
    } finally {
      picking.current = false;
    }
  }

  return (
    <View style={{ gap: 14 }}>
      <View style={{ flexDirection: 'row', gap: 10 }}>
        <View style={{ flex: 1 }}>
          <Button title="Fotoğraf çek" disabled={reading || saving} variant="deep" icon={<Camera size={18} color={colors.onDeep} />} onPress={() => pick('kamera')} />
        </View>
        <View style={{ flex: 1 }}>
          <Button title="Galeriden" disabled={reading || saving} variant="deep" icon={<ImagePlus size={18} color={colors.onDeep} />} onPress={() => pick('galeri')} />
        </View>
      </View>

      {pages.length === 0 ? (
        <Text variant="bodySmall" color="inkMuted" style={{ textAlign: 'center', paddingVertical: 24 }}>
          Henüz sayfa eklenmedi. Raporun her sayfası ayrı bir fotoğraf olarak eklenir.
        </Text>
      ) : (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 12, paddingVertical: 6 }}>
          {pages.map((uri, index) => (
            <Animated.View key={uri} entering={FadeIn} layout={LinearTransition.springify()} style={{ width: 120, gap: 6 }}>
              <Image source={{ uri }} style={{ width: 120, height: 160, borderRadius: 10, backgroundColor: colors.line }} />
              <Text variant="mono" color="inkMuted">{`sayfa ${index + 1}`}</Text>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                <Pressable disabled={reading || saving} accessibilityLabel="Sola taşı" hitSlop={8} onPress={() => onChange(movePage(pages, index, -1))}>
                  <ArrowLeft size={18} color={colors.ink} />
                </Pressable>
                <Pressable disabled={reading || saving} accessibilityLabel="Sayfayı sil" hitSlop={8} onPress={() => onChange(pages.filter((_, i) => i !== index))}>
                  <Trash2 size={18} color={colors.danger} />
                </Pressable>
                <Pressable disabled={reading || saving} accessibilityLabel="Sağa taşı" hitSlop={8} onPress={() => onChange(movePage(pages, index, 1))}>
                  <ArrowRight size={18} color={colors.ink} />
                </Pressable>
              </View>
            </Animated.View>
          ))}
        </ScrollView>
      )}

      {pages.map((uri, index) => (
        <View key={uri} style={{ gap: 8 }}>
          <Text variant="label">Sayfa {index + 1} · Okunan metin</Text>
          <Text selectable variant="bodySmall" color="inkMuted">
            {ocr[uri]?.status === 'loading' ? 'Rapor okunuyor…' : ocr[uri]?.status === 'done' ? ocr[uri].result?.metin || 'Bu fotoğrafta metin bulunamadı. Daha net bir fotoğraf deneyebilirsiniz.' : ocr[uri]?.error || 'Okuma bekleniyor…'}
          </Text>
          <Button title="Yeniden oku" variant="ghost" disabled={reading || saving} onPress={() => { void onRead([uri]); }} />
        </View>
      ))}
      <Text variant="bodySmall" color="inkMuted">Fotoğraflar yerel sunucuda okunur. Okunan metin hatalı olabilir; kontrol edin.</Text>
      <Button title="Taslağı kaydet" onPress={onSave} loading={saving} disabled={pages.length === 0 || reading} />
      <Button title="Geri: kimlik bilgileri" variant="ghost" disabled={reading || saving} onPress={onBack} />
    </View>
  );
}
