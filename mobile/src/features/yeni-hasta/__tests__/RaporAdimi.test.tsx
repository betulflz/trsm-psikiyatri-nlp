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
jest.mock('@/theme/ThemeProvider', () => ({ useTheme: () => ({ colors: {} }) }));
jest.mock('@/ui', () => {
  const { Text, Pressable } = require('react-native');
  return { Text, Button: ({ title, onPress, disabled, loading }: any) => <Pressable disabled={disabled || loading} onPress={onPress}><Text>{title}</Text></Pressable> };
});

const props = () => ({ pages: [], onChange: jest.fn(), onBack: jest.fn(), onSave: jest.fn(), saving: false, reading: false, ocr: {}, onRead: jest.fn(async () => {}) });

it.each(['kamera', 'galeri'])('%s fotoğrafı seçildiğinde otomatik OCR başlatılır', async (source) => {
  const pick = source === 'kamera' ? ImagePicker.launchCameraAsync : ImagePicker.launchImageLibraryAsync;
  (pick as jest.Mock).mockResolvedValue({ canceled: false, assets: [{ uri: 'file:///rapor.jpg' }] });
  const p = props();
  const screen = render(<RaporAdimi {...p} />);
  fireEvent.press(screen.getByText(source === 'kamera' ? 'Fotoğraf çek' : 'Galeriden'));
  await waitFor(() => expect(p.onRead).toHaveBeenCalledWith(['file:///rapor.jpg']));
  expect(p.onChange).toHaveBeenCalledWith(['file:///rapor.jpg']);
});

it('hata görünür ve aynı sayfa yeniden okunabilir', () => {
  const p = props();
  const screen = render(<RaporAdimi {...p} pages={['file:///rapor.jpg']} ocr={{ 'file:///rapor.jpg': { status: 'error', error: 'Okunamadı' } }} />);
  expect(screen.getByText('Okunamadı')).toBeTruthy();
  fireEvent.press(screen.getByText('Yeniden oku'));
  expect(p.onRead).toHaveBeenCalledWith(['file:///rapor.jpg']);
});

it('OCR sürerken taslak kaydedilemez', () => {
  const p = props();
  const screen = render(<RaporAdimi {...p} reading pages={['file:///rapor.jpg']} />);
  fireEvent.press(screen.getByText('Taslağı kaydet'));
  expect(p.onSave).not.toHaveBeenCalled();
});
