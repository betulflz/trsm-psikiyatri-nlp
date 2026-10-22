import { render } from '@testing-library/react-native';
import { ThemeProvider } from '@/theme/ThemeProvider';
import { palettes } from '@/theme/tokens';
import { Text } from '../Text';

jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock'),
);
jest.mock('expo-secure-store', () => ({}));

it('varyant yazı ailesini ve tema rengini uygular', () => {
  const { getByText } = render(
    <ThemeProvider>
      <Text variant="mono" color="inkMuted">
        Depakin
      </Text>
      <Text variant="title">Başlık</Text>
    </ThemeProvider>,
  );
  const mono = getByText('Depakin');
  expect(mono).toHaveStyle({ fontFamily: 'GeistMono_400Regular', color: palettes.light.inkMuted });
  expect(getByText('Başlık')).toHaveStyle({ fontFamily: 'Geist_800ExtraBold', fontSize: 24 });
});
