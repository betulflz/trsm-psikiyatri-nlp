import * as ImagePicker from 'expo-image-picker';
import { ArrowLeft, ArrowRight, Camera, ImagePlus, Trash2 } from 'lucide-react-native';
import { useRef, useState } from 'react';
import { Alert, Image, Pressable, ScrollView, TextInput, View } from 'react-native';
import Animated, { FadeIn, LinearTransition } from 'react-native-reanimated';
import { useTheme } from '@/theme/ThemeProvider';
import { fontFamily, radius } from '@/theme/tokens';
import { Button, Text } from '@/ui';
import { describeRemoved, type CropFraction } from './maske';
import { MaskeEditoru } from './MaskeEditoru';
import { movePage } from './taslak';
import type { PageOcr } from './ocr';

type Props = {
  pages: string[];
  onChange: (pages: string[]) => void;
  onBack: () => void;
  onSave: () => void;
  saving: boolean;
  ocr: Record<string, PageOcr>;
  reading: boolean;
  onRead: (uris: string[]) => Promise<void>;
  onCrop: (uri: string, crop: CropFraction | null) => void;
  onEditText: (uri: string, metin: string) => void;
  onSubmit: () => void;
  submitting: boolean;
  submitBlocker: string | null; // anonim kaydı engelleyen eksik (ör. doğum tarihi yok)
};

export function RaporAdimi({ pages, onChange, onBack, onSave, saving, ocr, reading, onRead, onCrop, onEditText, onSubmit, submitting, submitBlocker }: Props) {
  const { colors } = useTheme();
  const picking = useRef(false);
  const [toMask, setToMask] = useState<string[]>([]);
  const [consent, setConsent] = useState(false);
  const busy = reading || saving || submitting || toMask.length > 0;
  const allRead = pages.length > 0 && pages.every((uri) => ocr[uri]?.status === 'done' && ocr[uri].result?.metin.trim());

  function masked(maskedUri: string, crop: CropFraction | null) {
    setToMask((queue) => queue.slice(1));
    onCrop(maskedUri, crop);
    onChange([...pages, maskedUri]);
    setConsent(false);
    void onRead([maskedUri]);
  }

  async function pick(source: 'kamera' | 'galeri') {
    if (picking.current || busy) return;
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
      // Fotoğraflar önce karartma ekranından geçer; orijinal hiçbir zaman sunucuya gitmez.
      if (!result.canceled) setToMask([...new Set(result.assets.map((a) => a.uri))]);
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
          <Button title="Fotoğraf çek" disabled={busy} variant="deep" icon={<Camera size={18} color={colors.onDeep} />} onPress={() => pick('kamera')} />
        </View>
        <View style={{ flex: 1 }}>
          <Button title="Galeriden" disabled={busy} variant="deep" icon={<ImagePlus size={18} color={colors.onDeep} />} onPress={() => pick('galeri')} />
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
                <Pressable disabled={busy} accessibilityLabel="Sola taşı" hitSlop={8} onPress={() => onChange(movePage(pages, index, -1))}>
                  <ArrowLeft size={18} color={colors.ink} />
                </Pressable>
                <Pressable disabled={busy} accessibilityLabel="Sayfayı sil" hitSlop={8} onPress={() => onChange(pages.filter((_, i) => i !== index))}>
                  <Trash2 size={18} color={colors.danger} />
                </Pressable>
                <Pressable disabled={busy} accessibilityLabel="Sağa taşı" hitSlop={8} onPress={() => onChange(movePage(pages, index, 1))}>
                  <ArrowRight size={18} color={colors.ink} />
                </Pressable>
              </View>
            </Animated.View>
          ))}
        </ScrollView>
      )}

      {pages.map((uri, index) => {
        const page = ocr[uri];
        const removed = page?.status === 'done' ? describeRemoved(page.result?.temizlenen) : null;
        return (
          <View key={uri} style={{ gap: 8 }}>
            <Text variant="label">Sayfa {index + 1} · Okunan metin</Text>
            {page?.status === 'done' ? (
              <TextInput
                accessibilityLabel={`Sayfa ${index + 1} metni`}
                multiline
                value={page.result?.metin ?? ''}
                placeholder="Bu fotoğrafta metin bulunamadı. Daha net bir fotoğraf deneyebilirsiniz."
                placeholderTextColor={colors.inkMuted}
                onChangeText={(text) => { setConsent(false); onEditText(uri, text); }}
                style={{
                  minHeight: 120, textAlignVertical: 'top', backgroundColor: colors.surface, borderRadius: radius.input,
                  borderWidth: 1, borderColor: colors.line, padding: 12, fontFamily: fontFamily.mono, fontSize: 13, color: colors.ink,
                }}
              />
            ) : (
              <Text selectable variant="bodySmall" color="inkMuted">
                {page?.status === 'loading' ? page.progress || 'Fotoğraf gönderiliyor…' : page?.error || 'Okuma bekleniyor…'}
              </Text>
            )}
            {removed && <Text variant="label" color="primary">{removed}</Text>}
            <Button title="Yeniden oku" variant="ghost" disabled={busy} onPress={() => { void onRead([uri]); }} />
          </View>
        );
      })}
      <Text variant="bodySmall" color="inkMuted">
        Karartılmış fotoğraf sunucuda Qwen ile okunur ve saklanmaz. Bir sayfa birkaç dakika sürebilir. Okunan metin hatalı olabilir; düzeltip kimlik bilgisi kalmadığını kontrol edin.
      </Text>

      {allRead && (
        <View style={{ gap: 10, padding: 12, borderRadius: radius.input, borderWidth: 1, borderColor: colors.line }}>
          <Pressable
            accessibilityRole="checkbox"
            accessibilityState={{ checked: consent }}
            onPress={() => setConsent((c) => !c)}
            style={{ flexDirection: 'row', gap: 10, alignItems: 'flex-start' }}
          >
            <View style={{ width: 22, height: 22, borderRadius: 6, borderWidth: 2, borderColor: colors.primary, backgroundColor: consent ? colors.primary : 'transparent' }} />
            <Text variant="bodySmall" style={{ flex: 1 }}>
              Metinleri okudum; ad, TC, adres, telefon veya dosya numarası gibi kimlik bilgisi kalmadı.
            </Text>
          </Pressable>
          {submitBlocker && <Text variant="label" color="danger">{submitBlocker}</Text>}
          <Button title="Anonim kaydı sunucuya gönder" onPress={onSubmit} loading={submitting} disabled={!consent || !!submitBlocker || busy} />
          <Text variant="label" color="inkMuted">Sunucuya yalnızca yaş, cinsiyet ve bu metinler gider; ad ve TC gitmez.</Text>
        </View>
      )}

      <Button title="Taslağı cihaza kaydet" variant={allRead ? 'ghost' : 'primary'} onPress={onSave} loading={saving} disabled={pages.length === 0 || busy} />
      <Button title="Geri: kimlik bilgileri" variant="ghost" disabled={busy} onPress={onBack} />
      {toMask[0] && <MaskeEditoru key={toMask[0]} uri={toMask[0]} onDone={masked} onCancel={() => setToMask((queue) => queue.slice(1))} />}
    </View>
  );
}
