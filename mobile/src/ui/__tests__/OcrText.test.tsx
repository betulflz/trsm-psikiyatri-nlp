import { render } from '@testing-library/react-native';
import { ThemeProvider } from '@/theme/ThemeProvider';
import { palettes } from '@/theme/tokens';
import { OcrText } from '../OcrText';

jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock'),
);
jest.mock('expo-secure-store', () => ({}));

it('animasyonsuz modda ilaçları fosforlu, belirtileri altı çizili verir', () => {
  const { getByText } = render(
    <ThemeProvider>
      <OcrText
        text="Depakin devam, uykusuzluk"
        highlights={[
          { bas: 0, son: 7, tur: 'ilac' },
          { bas: 15, son: 25, tur: 'belirti' },
        ]}
        animate={false}
      />
    </ThemeProvider>,
  );
  expect(getByText('Depakin')).toHaveStyle({ backgroundColor: palettes.light.highlight });
  expect(getByText('uykusuzluk')).toHaveStyle({ textDecorationLine: 'underline' });
});
