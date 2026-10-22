import { Search, X } from 'lucide-react-native';
import { Pressable, TextInput, View } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';
import { fontFamily, radius } from '@/theme/tokens';

type Props = { value: string; onChangeText: (value: string) => void; placeholder: string };

export function SearchField({ value, onChangeText, placeholder }: Props) {
  const { colors } = useTheme();
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        backgroundColor: colors.surface,
        borderRadius: radius.input,
        borderWidth: 1,
        borderColor: colors.line,
        paddingHorizontal: 12,
      }}
    >
      <Search size={18} color={colors.inkMuted} strokeWidth={2} />
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={colors.inkMuted}
        autoCorrect={false}
        style={{ flex: 1, paddingVertical: 11, fontFamily: fontFamily[500], fontSize: 15, color: colors.ink }}
      />
      {value.length > 0 && (
        <Pressable accessibilityLabel="Aramayı temizle" onPress={() => onChangeText('')} hitSlop={10}>
          <X size={18} color={colors.inkMuted} strokeWidth={2} />
        </Pressable>
      )}
    </View>
  );
}
