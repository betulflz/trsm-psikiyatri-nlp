import { View } from 'react-native';
import { Button, FormField, SegmentedControl, Text } from '@/ui';
import { DateField } from './DateField';
import type { KimlikForm } from './dogrulama';

type Props = {
  form: KimlikForm;
  errors: Partial<Record<keyof KimlikForm, string>>;
  onChange: (patch: Partial<KimlikForm>) => void;
  onNext: () => void;
};

export function KimlikAdimi({ form, errors, onChange, onNext }: Props) {
  return (
    <View style={{ gap: 14 }}>
      <FormField label="Ad soyad *" value={form.adSoyad} onChangeText={(adSoyad) => onChange({ adSoyad })} autoCapitalize="words" error={errors.adSoyad} />
      <View style={{ gap: 6 }}>
        <Text variant="label" color="inkMuted">
          Cinsiyet
        </Text>
        <SegmentedControl<'Kadın' | 'Erkek' | 'belirsiz'>
          value={form.cinsiyet ?? 'belirsiz'}
          onChange={(v) => onChange({ cinsiyet: v === 'belirsiz' ? null : v })}
          options={[
            { value: 'Kadın', label: 'Kadın' },
            { value: 'Erkek', label: 'Erkek' },
            { value: 'belirsiz', label: 'Belirtilmedi' },
          ]}
        />
      </View>
      <DateField label="Doğum tarihi" value={form.dogumTarihi} onChange={(dogumTarihi) => onChange({ dogumTarihi })} error={errors.dogumTarihi} />
      <FormField
        label="T.C. Kimlik No"
        value={form.tcKimlik}
        onChangeText={(t) => onChange({ tcKimlik: t.replace(/\D/g, '').slice(0, 11) })}
        keyboardType="number-pad"
        maxLength={11}
        mono
        error={errors.tcKimlik}
        placeholder="11 hane"
      />
      <Button title="Devam: rapor sayfaları" onPress={onNext} />
    </View>
  );
}
