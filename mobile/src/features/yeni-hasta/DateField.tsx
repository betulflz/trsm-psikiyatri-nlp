import DateTimePicker from '@react-native-community/datetimepicker';
import { useState } from 'react';
import { Platform, View } from 'react-native';
import { formatDate } from '@/lib/format';
import { useTheme } from '@/theme/ThemeProvider';
import { radius } from '@/theme/tokens';
import { PressableScale, Text } from '@/ui';

type Props = { label: string; value: string | null; onChange: (iso: string) => void; error?: string };

function toIso(date: Date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function DateField({ label, value, onChange, error }: Props) {
  const { colors, name } = useTheme();
  const [open, setOpen] = useState(false);
  const current = value ? new Date(`${value}T12:00:00`) : new Date(1990, 0, 1);
  return (
    <View style={{ gap: 6 }}>
      <Text variant="label" color="inkMuted">
        {label}
      </Text>
      {Platform.OS === 'ios' ? (
        <View style={{ alignItems: 'flex-start' }}>
          <DateTimePicker
            value={current}
            mode="date"
            display="compact"
            maximumDate={new Date()}
            locale="tr-TR"
            themeVariant={name}
            accentColor={colors.primary}
            onChange={(_, date) => date && onChange(toIso(date))}
          />
        </View>
      ) : (
        <>
          <PressableScale
            accessibilityLabel={label}
            onPress={() => setOpen(true)}
            style={{ backgroundColor: colors.surface, borderRadius: radius.input, borderWidth: 1, borderColor: error ? colors.danger : colors.line, padding: 12 }}
          >
            <Text variant="body" color={value ? 'ink' : 'inkMuted'}>
              {value ? formatDate(value) : 'Tarih seçin'}
            </Text>
          </PressableScale>
          {open && (
            <DateTimePicker
              value={current}
              mode="date"
              maximumDate={new Date()}
              onChange={(event, date) => {
                setOpen(false);
                if (event.type === 'set' && date) onChange(toIso(date));
              }}
            />
          )}
        </>
      )}
      {error ? (
        <Text variant="label" color="danger">
          {error}
        </Text>
      ) : null}
    </View>
  );
}
