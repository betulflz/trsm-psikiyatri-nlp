import { fireEvent, render, waitFor } from '@testing-library/react-native';
import * as ImagePicker from 'expo-image-picker';
import { RaporAdimi } from '../RaporAdimi';

jest.mock('lucide-react-native', () => ({ ArrowLeft: () => null, ArrowRight: () => null, Camera: () => null, ImagePlus: () => null, Trash2: () => null }));
jest.mock('react-native-reanimated', () => ({
  __esModule: true,
  default: { View: require('react-native').View },
  FadeIn: undefined,
  LinearTransition: { springify: () => undefined },
}));

jest.mock('expo-image-picker', () => ({
  requestCameraPermissionsAsync: jest.fn(async () => ({ granted: true })),
  requestMediaLibraryPermissionsAsync: jest.fn(async () => ({ granted: true })),
  launchCameraAsync: jest.fn(),
  launchImageLibraryAsync: jest.fn(),
}));
jest.mock('../taslak', () => ({ movePage: jest.fn() }));
jest.mock('../MaskeEditoru', () => ({
  MaskeEditoru: ({ uri, onDone }: any) => {
    const { Pressable, Text } = require('react-native');
    return <Pressable onPress={() => onDone(uri.replace('.jpg', '-maskeli.jpg'), { x: 0, y: 0.1, w: 1, h: 0.5 })}><Text>{`maske:${uri}`}</Text></Pressable>;
  },
}));
jest.mock('@/theme/ThemeProvider', () => ({ useTheme: () => ({ colors: {} }) }));
jest.mock('@/ui', () => {
  const { Text, Pressable } = require('react-native');
  return { Text, Button: ({ title, onPress, disabled, loading }: any) => <Pressable accessibilityState={{ disabled: !!(disabled || loading) }} disabled={disabled || loading} onPress={onPress}><Text>{title}</Text></Pressable> };
});

const props = () => ({
  pages: [] as string[], onChange: jest.fn(), onBack: jest.fn(), onSave: jest.fn(), saving: false, reading: false, ocr: {},
  onRead: jest.fn(async () => {}), onCrop: jest.fn(), onEditText: jest.fn(), onSubmit: jest.fn(), submitting: false, submitBlocker: null as string | null,
});
const done = { 'file:///r.jpg': { status: 'done' as const, result: { metin: 'Ad Soyad: [GİZLİ]\nSertralin 50 mg', motor: 'q', temizlenen: { ad: 1, tc: 1 } } } };

it.each(['kamera', 'galeri'])('%s fotoğrafı önce karartılır, sunucuya yalnızca karartılmış kopya gider', async (source) => {
  const pick = source === 'kamera' ? ImagePicker.launchCameraAsync : ImagePicker.launchImageLibraryAsync;
  (pick as jest.Mock).mockResolvedValue({ canceled: false, assets: [{ uri: 'file:///rapor.jpg' }] });
  const p = props();
  const screen = render(<RaporAdimi {...p} />);
  fireEvent.press(screen.getByText(source === 'kamera' ? 'Fotoğraf çek' : 'Galeriden'));
  await waitFor(() => expect(screen.getByText('maske:file:///rapor.jpg')).toBeTruthy());
  expect(p.onRead).not.toHaveBeenCalled();
  fireEvent.press(screen.getByText('maske:file:///rapor.jpg'));
  expect(p.onChange).toHaveBeenCalledWith(['file:///rapor-maskeli.jpg']);
  expect(p.onRead).toHaveBeenCalledWith(['file:///rapor-maskeli.jpg']);
  expect(p.onCrop).toHaveBeenCalledWith('file:///rapor-maskeli.jpg', { x: 0, y: 0.1, w: 1, h: 0.5 });
});

it('hata görünür ve aynı sayfa yeniden okunabilir', () => {
  const p = props();
  const screen = render(<RaporAdimi {...p} pages={['file:///rapor.jpg']} ocr={{ 'file:///rapor.jpg': { status: 'error', error: 'Okunamadı' } }} />);
  expect(screen.getByText('Okunamadı')).toBeTruthy();
  fireEvent.press(screen.getByText('Yeniden oku'));
  expect(p.onRead).toHaveBeenCalledWith(['file:///rapor.jpg']);
});

it('OCR sürerken taslak kaydedilemez ve anonim kayıt görünmez', () => {
  const p = props();
  const screen = render(<RaporAdimi {...p} reading pages={['file:///rapor.jpg']} />);
  fireEvent.press(screen.getByText('Taslağı cihaza kaydet'));
  expect(p.onSave).not.toHaveBeenCalled();
  expect(screen.queryByText('Anonim kaydı sunucuya gönder')).toBeNull();
});

it('okunan metin düzenlenebilir ve silinenler özeti görünür', () => {
  const p = props();
  const screen = render(<RaporAdimi {...p} pages={['file:///r.jpg']} ocr={done} />);
  expect(screen.getByText('Otomatik silinenler: 1 ad, 1 TC no')).toBeTruthy();
  fireEvent.changeText(screen.getByLabelText('Sayfa 1 metni'), 'Sertralin 50 mg');
  expect(p.onEditText).toHaveBeenCalledWith('file:///r.jpg', 'Sertralin 50 mg');
});

it('anonim kayıt yalnızca kimlik onayından sonra gönderilir', () => {
  const p = props();
  const screen = render(<RaporAdimi {...p} pages={['file:///r.jpg']} ocr={done} />);
  fireEvent.press(screen.getByText('Anonim kaydı sunucuya gönder'));
  expect(p.onSubmit).not.toHaveBeenCalled();
  fireEvent.press(screen.getByRole('checkbox'));
  fireEvent.press(screen.getByText('Anonim kaydı sunucuya gönder'));
  expect(p.onSubmit).toHaveBeenCalled();
});

it('eksik bilgi varsa onaylansa da gönderilemez', () => {
  const p = props();
  const screen = render(<RaporAdimi {...p} pages={['file:///r.jpg']} ocr={done} submitBlocker="Doğum tarihi gerekli" />);
  expect(screen.getByText('Doğum tarihi gerekli')).toBeTruthy();
  fireEvent.press(screen.getByRole('checkbox'));
  fireEvent.press(screen.getByText('Anonim kaydı sunucuya gönder'));
  expect(p.onSubmit).not.toHaveBeenCalled();
});
