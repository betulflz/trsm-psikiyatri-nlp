import * as ImagePicker from 'expo-image-picker';
import { ArrowLeft, ArrowRight, Camera, ImagePlus, Trash2 } from 'lucide-react-native';
import { Alert, Image, Pressable, ScrollView, View } from 'react-native';
import Animated, { FadeIn, LinearTransition } from 'react-native-reanimated';
import { useTheme } from '@/theme/ThemeProvider';
import { Button, Text } from '@/ui';
import { movePage } from './taslak';

type Props = { pages: string[]; onChange: (pages: string[]) => void; onBack: () => void; onSave: () => void; saving: boolean };

export function RaporAdimi({ pages, onChange, onBack, onSave, saving }: Props) {
  const { colors } = useTheme();

  async function pick(source: 'kamera' | 'galeri') {
    const permission =
      source === 'kamera' ? await ImagePicker.requestCameraPermissionsAsync() : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('İzin gerekli', source === 'kamera' ? 'Kamera izni verilmedi.' : 'Galeri izni verilmedi.');
      return;
    }
    const options: ImagePicker.ImagePickerOptions = { mediaTypes: ['images'], quality: 0.7, allowsMultipleSelection: source === 'galeri' };
    const result = source === 'kamera' ? await ImagePicker.launchCameraAsync(options) : await ImagePicker.launchImageLibraryAsync(options);
    if (!result.canceled) onChange([...pages, ...result.assets.map((a) => a.uri)]);
  }

  return (
    <View style={{ gap: 14 }}>
      <View style={{ flexDirection: 'row', gap: 10 }}>
        <View style={{ flex: 1 }}>
          <Button title="Fotoğraf çek" variant="deep" icon={<Camera size={18} color={colors.onDeep} />} onPress={() => pick('kamera')} />
        </View>
        <View style={{ flex: 1 }}>
          <Button title="Galeriden" variant="deep" icon={<ImagePlus size={18} color={colors.onDeep} />} onPress={() => pick('galeri')} />
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
                <Pressable accessibilityLabel="Sola taşı" hitSlop={8} onPress={() => onChange(movePage(pages, index, -1))}>
                  <ArrowLeft size={18} color={colors.ink} />
                </Pressable>
                <Pressable accessibilityLabel="Sayfayı sil" hitSlop={8} onPress={() => onChange(pages.filter((_, i) => i !== index))}>
                  <Trash2 size={18} color={colors.danger} />
                </Pressable>
                <Pressable accessibilityLabel="Sağa taşı" hitSlop={8} onPress={() => onChange(movePage(pages, index, 1))}>
                  <ArrowRight size={18} color={colors.ink} />
                </Pressable>
              </View>
            </Animated.View>
          ))}
        </ScrollView>
      )}

      <Button title="Taslağı kaydet" onPress={onSave} loading={saving} disabled={pages.length === 0} />
      <Button title="Geri: kimlik bilgileri" variant="ghost" onPress={onBack} />
    </View>
  );
}
